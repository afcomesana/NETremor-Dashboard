import { colorCode, axisTitles } from "./constants.js";


export default class Plotter {

    constructor() {

        // Find div container where the chart will be displayed:
        this.recordChartContainer  = document.getElementById("record-chart-container");
        this.chartGroupContainerId = "record-chart-container-svg"

        // Milliseconds that two samples have to apart in order to be considered to belong to different chunks
        this.lineChunkThreshold = 2000

        // Define chart size:
        this.margin = {
            top: 10,
            right: 30,
            bottom: 30,
            left: 0
        };

        this.width  = this.recordChartContainer.clientWidth - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;

        this.transitionMillis = 500;

        this.xAxisId      = "chart-x-axis";
        this.yAxisId      = "chart-y-axis";
        this.yAxisTitleId = "y-axis-title";

        this.trialOption    = null;
        this.selectedSensor = null;
        this.selectedPlot   = null;
        this.selectedMetric = null;

        this.axisElements = Array.from(document.getElementsByClassName("axis-filter"))
        this.axis = this.axisElements.map(axis => axis.id.split("-")[1]);

        this.RECORD_TYPE = document.getElementById("record-type")
        if ( !this.RECORD_TYPE ) {
            throw "Could not define record type.";
        }

        this.RECORD_TYPE = this.RECORD_TYPE.value;

        this.IS_AMBULATORY_RECORD = this.RECORD_TYPE == "ambulatory";
        this.IS_CONTINUOUS_RECORD = this.RECORD_TYPE == "continuous";
    }

    initChart = () => {

        if ( document.getElementById(this.chartGroupContainerId) ) return


        // SVG that will contain the chart:
        this.svg = d3.select(this.recordChartContainer)
            .html(null)
            .append("svg")
            .attr("width", this.width + this.margin.left + this.margin.right)
            .attr("height", this.height + this.margin.top + this.margin.bottom)
            .append("g")
            .attr("id", this.chartGroupContainerId)
            .attr("style", "overflow:scroll")

        console.log("wheel event listener")
        document.getElementById(this.chartGroupContainerId).addEventListener("wheel", this.updateChart)

        // Clip path:
        this.clip = this.svg.append("defs")
            // The <defs> element is used to store graphical objects
            // that will be used at a later time. Objects created inside
            // a <defs> element are not rendered directly. To display
            // them you have to reference them (with a <use> element for
            // example).
            .append("svg:clipPath")
            // The clip-path CSS property creates a clipping region that
            // sets what part of an element should be shown. Parts that
            // are inside the region are shown, while those outside are
            // hidden.
            .attr("id", "clip")
                .append("svg:rect")
                .attr("width", this.width)
                .attr("height", this.height)
                .attr("x", 0)
                .attr("y", 0);

        
        // Group that will contain the lines
        this.lineGroup = this.svg.append("g")
            .attr("clip-path", "url(#clip)")
    }

    getCsrfToken = () => {
        // CSRF token to make the request
        let csrfToken = document.cookie.split(";").find(cookie => cookie.includes("csrftoken"));
        if ( !csrfToken ) {
            // Show error message
            throw "No csrf token";
        }

        return csrfToken.split("=")[1];
    }

    getPlotOptions = () => {
        
        // Get selected option, sensor and axis
        this.trialOption    = document.querySelector(".trial-option.selected");
        this.selectedSensor = document.querySelector(".sensor-filter.selected");
        this.selectedMetric = document.querySelector(".metric-option.selected");
        this.selectedAxis   = Array.from(document.querySelectorAll(".axis-filter.selected"));
        this.plotSelection  = document.getElementById("plot-selection").value.split("-").map(parseFloat);

        if ( !this.trialOption && this.IS_AMBULATORY_RECORD ) {
            console.error("No option selected");
            return;
        }


        if ( !this.selectedSensor ) {
            console.error("No sensor selected.");
            return;
        }


        if ( !this.selectedMetric ) {
            console.error("No metric selected.");
            return;
        }

        this.selectedSensor = this.selectedSensor.id.split("-")[1];
        this.selectedMetric = this.selectedMetric.id.split("-")[1];
        this.selectedAxis   = this.selectedAxis.map(axis => axis.id.split("-")[1]);
    }

    loadData = async () => {

        this.getPlotOptions();

        if ( this.RECORD_TYPE == "ambulatory" ) {

            let { id } = this.trialOption.dataset;

            if ([this.selectedMetric, id].join("-") != this.selectedPlot) {
    
                // Update selected plot option
                this.selectedPlot = [this.selectedMetric, id].join("-");

                id = id.split("-").map(item => parseInt(item))

                this.data = await this.fetchData({
                    metric: this.selectedMetric,
                    id
                });
            }

            this.sensorData = this.data.filter(sample => sample.sensor == this.selectedSensor);

        } else if ( this.RECORD_TYPE == "continuous" ) {

            const selectedPlot = [this.selectedMetric, this.selectedSensor, this.plotSelection.join("-")].join("-");
            console.log(`selected plot: ${selectedPlot}`);

            if ( selectedPlot != this.selectedPlot ) {

                this.selectedPlot = selectedPlot;

                this.data = await this.fetchData({
                    sensor: this.selectedSensor,
                    metric: this.selectedMetric,
                    samples: this.width,
                    selection: this.plotSelection
                });

                // const initialTimestamp = 1705600000000; 

                // if ( !this.data ) {
                //     this.data = data;
                // } else {
                    
                //     const timestamps = this.data.map(item => item.timestamp);
                //     this.data = [
                //         ...this.data,
                //         ...data.filter(item => !timestamps.includes(item.timestamp))
                //     ];

                //     this.data.sort((a, b) => {
                //         if ( a.timestamp < b.timestamp ) return -1;
                //         if ( a.timestamp >= b.timestamp ) return 1;
                //     });
                    
                // }
                // console.log(this.data[0].timestamp - initialTimestamp, this.data.slice(-1)[0].timestamp - initialTimestamp)
                // console.log(this.data)
            }

            this.sensorData = this.data;
        }
    }


    fetchData = async params => {

        const CRSF_TOKEN = this.getCsrfToken();

        let data;

        try {

            this.showSpinner(`#${this.recordChartContainer.id}`);

            // TODO: Take into account the width of the chart container:
            const response = await fetch(window.location.pathname, {
                method: "POST",
                headers: {"X-CSRFToken": CRSF_TOKEN, "Content-type": "application/json"},
                body: JSON.stringify(params)
            })

            if ( !response.ok ) {
                console.error(`Error fetching data: ${await response.text()}`);
                this.hideSpinner()
                return;
            }

            data = await response.json();
            this.hideSpinner()

        } catch(error) {
            data = null;
            throw(`Could not load data to plot the chart.\n${error}`)
        }

        return data;
    }

    renderChart = async () => {

        if ( !this.sensorData ) {
            this.recordChartContainer.innerHTML = "No hay datos."
            return
        }


        // If there is something to plot, initialize the chart.
        this.initChart();

        // Show colors of the lines
        this.updateLegend();
        
        // X-Axis
        this.xScale = d3.scaleTime()
            .domain(d3.extent(this.sensorData, item => new Date(item.timestamp)))
            .range([0, this.width]);

        document.getElementById(this.xAxisId)?.remove()
        this.xAxis  = this.svg.append("g")
            .attr("id", this.xAxisId)
            .attr("transform", `translate(0, ${this.height})`)
            .call(d3.axisBottom(this.xScale).tickFormat(d3.timeFormat("%H:%M:%S")));
        

        // Y-Axis
        this.yScale = d3.scaleLinear()
            // TODO: Change getDataDomain function to take into account
            // only selected axis
            .domain(this.getDataDomain())
            .range([this.height, 0]);

        document.getElementById(this.yAxisId)?.remove();
        this.yAxis  = this.svg.append("g")
            .attr("id", this.yAxisId)
            .call(d3.axisLeft(this.yScale));

        
        document.getElementById(this.yAxisTitleId)?.remove();
        this.svg.append("text")
            .attr("id", this.yAxisTitleId)
            .attr("transform", `translate(-30, ${Math.floor(this.height/2)}) rotate(-90) `)
            .html(axisTitles[this.selectedSensor]);
    
        const { width: yAxisWidth }      = document.getElementById(this.yAxisId).getBoundingClientRect()
        const { width: yAxisTitleWidth } = document.getElementById(this.yAxisTitleId).getBoundingClientRect()
        
        d3.select(`#${this.chartGroupContainerId}`)
            .attr("transform", `translate(${Math.ceil(yAxisWidth + yAxisTitleWidth)}, ${this.margin.top})`)



        // Plot:
        const linesToFlush = Array.from(this.recordChartContainer.getElementsByClassName("line"));
        linesToFlush.forEach(line => line.remove());
        this.axis.forEach(axis => {
            this.drawLine(this.selectedSensor, axis, this.sensorData);
        });
    }


    updateLegend = () => {
        this.getPlotOptions();

        if ( !this.selectedSensor ) {
            console.error("There is no sensor selected.");
            return;
        }

        if ( !this.axis ) {
            console.error("There are no axis selected.");
            return;
        }

        if ( !this.axisElements ) {
            console.error("There are no axis elements in DOM.");
            return;
        }

        
        this.axisElements.forEach(axisElement => {
            const axis = axisElement.id.split("-")[1]

            if ( this.selectedAxis.includes(axis) ) {
                axisElement.style.background = colorCode[`${this.selectedSensor}-${axis}`];
                axisElement.style.color = "white";
            } else {
                axisElement.style.background = "none";
                axisElement.style.color = "black";
            }
        });

    }

    /**
     * 
     * @param {Array} axis - array with all the selected axis by the user
     * @returns {Array} being the first element the minimum value along all the axis and the
     * second element the maximum value along all the axis
     */
    getDataDomain = () => {
        let domain = this.axis.map(axis => d3.extent(this.sensorData, d => d[axis]))

        return [
            Math.min(...domain.map(axisDomain => axisDomain[0])), // minimum of all axis
            Math.max(...domain.map(axisDomain => axisDomain[1])), // maximum of all axis
        ]
    }

    drawLine = (sensor, axis, data) => {

        // let chunks = [],
        //     lastChunkIndex = 0

        // data.forEach((item, index) => {
        //     if ( !!index && item.timestamp - data[index - 1].timestamp > this.lineChunkThreshold) {
        //         chunks.push(data.slice(lastChunkIndex, index - 1))
        //         lastChunkIndex = index
        //     }
        // });
    
        // data = chunks        
        // delete window.chunks

        // data.forEach((chunk, index) => {
        //     const lineId = `${sensor}-${axis}-${index}-line`;
    
        //     // If the line wasn't already drawn, 
        //     if (!document.getElementById(lineId)) {
        //         this.lineGroup.append("path")
        //             .datum(chunk)
        //             .attr("id", lineId)
        //             .attr("class", `line ${sensor} ${axis}`)
        //             .attr("fill", "none")
        //             .attr("stroke", "steelblue")
        //             .attr("stroke-width", 1.5)
        //             .attr("d", d3.line()
        //                 .x(d => this.xScale(d.timestamp))
        //                 .y(d => this.yScale(d[axis]))
        //             )
        //     }
        // })

        const lineId = `${sensor}-${axis}-line`;
        
        // If the line wasn't already drawn, 
        document.getElementById(lineId)?.remove();
        this.lineGroup.append("path")
            .datum(data)
            .attr("id", lineId)
            .attr("class", `line ${sensor} ${axis} ${this.selectedAxis.includes(axis) ? "" : "opacity-0"}`)
            .attr("fill", "none")
            .attr("stroke", colorCode[`${sensor}-${axis}`])
            .attr("stroke-width", 1.5)
            .attr("d", d3.line()
                .x(d => this.xScale(d.timestamp))
                .y(d => this.yScale(d[axis]))
            )
    }

    updateChart = async event => {
        console.log(event)
        // const { selection } = event;

        // if ( !selection ) {
        //     if ( !this.idledTimeout ) return this.idledTimeout = setTimeout(this.idled, 350);
        //     this.xScale.domain(d3.extent(this.sensorData, d => new Date(parseInt(d.timestamp))));


        // // Fetch again to get amplified data:
        // } else {

        //     // Fetch new samples for the new interval:
        //     if ( this.IS_CONTINUOUS_RECORD ) {
        //         let [startSelection, endSelection] = selection;
        //         document.getElementById("plot-selection").value = `${startSelection/this.width}-${endSelection/this.width}`

        //         await this.loadData();
        //         this.renderChart();
        //     }

        //     this.xScale.domain([this.xScale.invert(selection[0]), this.xScale.invert(selection[1])]);
        //     this.lineGroup.select(".brush").call(this.brush.move, null);
        // }

        // this.xAxis.transition().duration(this.transitionMillis).call(d3.axisBottom(this.xScale))

        // Array.from(document.getElementsByClassName("line")).forEach(line => {
        //     const axis = line.id.split("-")[1]
        //     d3.select(line)
        //         .transition()
        //         .duration(this.transitionMillis)
        //         .attr("d", d3.line()
        //             .x(d => this.xScale(d.timestamp))
        //             .y(d => this.yScale(d[axis]))
        //         )
        // });

        // // Restart original data with no specific time selected
        // this.svg.on("dbclick", () => {
        //     console.log("db click event")
        //     this.xScale.domain(d3.extent(this.data, d => d.timestamp))
        //     this.xAxis.transition().call(d3.axisBottom(this.xScale))
        //     this.lineGroup.select(".line")
        //         .transition()
        //         .attr("d", d3.line()
        //             .x(d => this.xScale(d.timestamp))
        //             .y(d => this.yScale(d.x))
        //         )
        // });
    }

    
    // --------------
    // HANDLE SPINNER
    // --------------
    showSpinner = selector => {

        this.hideSpinner(selector);

        const loadLayout = document.createElement("div")
        loadLayout.className = "load-layout"
        loadLayout.innerHTML = `<div class="load-spinner"><div></div><div></div><div></div><div></div></div>`
        // `<div class="load-layout"><div class="load-spinner"><div></div><div></div><div></div><div></div></div></div>`
        document.querySelector(selector).appendChild(loadLayout)
    }

    hideSpinner = (selector = null) => {
        // If selector is provided, remove only spinner inside that element.
        // Othervise delete all the spinner in the DOM
        const container = !!selector ? document.querySelector(selector) : document
        Array.from(container.getElementsByClassName("load-layout")).forEach(spinner => spinner.remove())
    }
}