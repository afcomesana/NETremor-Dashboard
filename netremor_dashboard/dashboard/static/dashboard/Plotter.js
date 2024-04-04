import { colorCode, axisTitles } from "./constants.js";


export default class Plotter {

    constructor() {

        // -----------------------------------
        // CHART ELEMENT, SIZES AND FEATURES:
        // -----------------------------------
        this.recordChartContainer  = document.getElementById("record-chart-container");
        this.chartGroupContainerId = "record-chart-container-group"
        this.xAxisElementId        = "chart-x-axis";
        this.yAxisElementId        = "chart-y-axis";
        this.yAxisElementTitleId   = "y-axis-title";
        this.axisElements          = Array.from(document.getElementsByClassName("axis-filter"))
        this.axis                  = this.axisElements.map(axis => axis.id.split("-")[1]);

        this.margin = {
            top: 10,
            right: 30,
            bottom: 30,
            left: 50
        };
        this.width  = this.recordChartContainer.clientWidth - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;

        this.lineChunkThreshold = 2000;
        this.transitionMillis   = 500;
        this.lineStrokeWidth    = 1.5;
        this.zoomScale          = 1;

        // --------------------------------
        // FILTERS AND CHART OPTIONS:
        // --------------------------------
        this.trialOption    = null;
        this.selectedSensor = null;
        this.selectedPlot   = null;
        this.selectedMetric = null;


        // -------------------------------------------------------
        // AWARENESS OF THE TYPE OF RECORD THAT IS BEING PLOTTED:
        // -------------------------------------------------------
        this.RECORD_TYPE = document.getElementById("record-type")
        if ( !this.RECORD_TYPE ) {
            throw "Could not define record type.";
        }

        this.RECORD_TYPE = this.RECORD_TYPE.value;

        this.IS_AMBULATORY_RECORD = this.RECORD_TYPE == "ambulatory";
        this.IS_CONTINUOUS_RECORD = this.RECORD_TYPE == "continuous";
    }

    initChart = () => {

        // This will only be called one time during all the DOM lifetime of the chart:
        if ( document.getElementById(this.chartGroupContainerId) ) {
            return;
        }

        // SVG that will contain the chart:
        this.svg = d3.select(this.recordChartContainer)
            .html(null) // Wipe out anything that could be rendered in the chart's area
            .append("svg")
            .attr("width", this.width + this.margin.left + this.margin.right)
            .attr("height", this.height + this.margin.top + this.margin.bottom)
            .attr("id", "record-chart-container-svg");

        this.chartGroupContainer = this.svg.append("g")
            .attr("id", this.chartGroupContainerId)
            .attr("pointer-events", "all")
            .attr("transform", `translate(${this.margin.left}, ${this.margin.top})`);

        // Clip path:
        this.clip = this.chartGroupContainer.append("defs")
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
        this.lineGroup = this.chartGroupContainer.append("g")
            .attr("id", "record-line-group")
            .attr("pointer-events", "all")
            .attr("clip-path", "url(#clip)");
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

        if ( !this.trialOption && this.IS_AMBULATORY_RECORD ) {
            console.error("No option selected");
            return;
        }

        if ( this.trialOption && this.IS_CONTINUOUS_RECORD ) {
            this.timeRange = this.trialOption.dataset.range.split("-").map(el => parseInt(el));
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

            let { trial, id: taskId } = this.trialOption.dataset;

            if ([this.selectedMetric, taskId, trial].join("-") != this.selectedPlot) {
    
                // Update selected plot option
                this.selectedPlot = [this.selectedMetric, trial].join("-");

                this.data = await this.fetchData({
                    metric: this.selectedMetric,
                    trial,
                    taskId
                });
            }

            this.sensorData = this.data.filter(sample => sample.sensor == this.selectedSensor);

        } else if ( this.RECORD_TYPE == "continuous" ) {

            if ( !this.timeRange ) {
                this.timeRange = false;
            }

            const selectedPlot = [this.selectedMetric, this.selectedSensor, this.timeRange].join("-");
            if ( selectedPlot != this.selectedPlot ) {

                this.selectedPlot = selectedPlot;

                this.data = await this.fetchData({
                    sensor: this.selectedSensor,
                    metric: this.selectedMetric,
                    samples: this.width,
                    timeRange: this.timeRange
                });
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
            this.recordChartContainer.innerHTML = "No hay datos.";
            return
        }

        // If there is something to plot, initialize the chart.
        this.initChart();

        switch(this.selectedMetric) {

            case("spectrogram"):
                console.log("plotting spectrogram")
                this.plotSpectrogram();
                break;

            default:
                console.log("plotting raw data")
                this.plotRawData();
                break;
        }

    }

    plotRawData = () => {

        // Show colors of the lines
        this.updateLegend();

        // X-Axis
        this.xScale = d3.scaleTime()
            .domain(d3.extent(this.sensorData, item => new Date(item.timestamp)))
            .range([0, this.width]);

        this.xAxis = d3.axisBottom(this.xScale).tickFormat(d3.timeFormat("%H:%M:%S"))

        document.getElementById(this.xAxisElementId)?.remove()
        this.xAxisElement  = this.chartGroupContainer.append("g")
            .attr("id", this.xAxisElementId)
            .attr("transform", `translate(0, ${this.height})`)
            .call(this.xAxis);
        
        
        this.xAxisElementWidth   = this.xAxisElement.node().getBoundingClientRect().width;
        this.xAxisElementOffsetX = this.xAxisElement.node().getBoundingClientRect().x;

        // Y-Axis
        this.yScale = d3.scaleLinear()
            .domain(this.getRawDataDomain())
            .range([this.height, 0]);

        this.yAxis = d3.axisLeft(this.yScale);

        document.getElementById(this.yAxisElementId)?.remove();
        this.yAxisElement = this.chartGroupContainer.append("g")
            .attr("id", this.yAxisElementId)
            .call(this.yAxis);

        
        document.getElementById(this.yAxisElementTitleId)?.remove();
        this.chartGroupContainer.append("text")
            .attr("id", this.yAxisElementTitleId)
            .attr("transform", `translate(-30, ${Math.floor(this.height/2)}) rotate(-90) `)
            .html(axisTitles[this.selectedSensor]);

        // Plot:
        const linesToFlush = Array.from(this.recordChartContainer.getElementsByClassName("line"));
        linesToFlush.forEach(line => line.remove());
        this.axis.forEach(axis => {
            this.drawLine(this.selectedSensor, axis, this.sensorData);
        });
    }

    plotSpectrogram = () => {
        // X-Axis
        this.xScale = d3.scaleBand()
            .domain([...Array(this.sensorData.length).keys()])
            .range([0, this.width]);

       this.xAxis = d3.axisBottom(this.xScale);


       document.getElementById(this.xAxisElementId)?.remove()
       this.xAxisElement  = this.chartGroupContainer.append("g")
           .attr("id", this.xAxisElementId)
           .attr("transform", `translate(0, ${this.height})`)
           .call(this.xAxis);
       
       
       this.xAxisElementWidth   = this.xAxisElement.node().getBoundingClientRect().width;
       this.xAxisElementOffsetX = this.xAxisElement.node().getBoundingClientRect().x;

       // Y-Axis
       this.yScale = d3.scaleBand()
           .domain([...Array(this.sensorData[0].psd.length).keys()])
           .range([this.height, 0]);

       this.yAxis = d3.axisLeft(this.yScale);

       document.getElementById(this.yAxisElementId)?.remove();
       this.yAxisElement = this.chartGroupContainer.append("g")
           .attr("id", this.yAxisElementId)
           .call(this.yAxis);

        var myColor = d3.scaleSequential()
           .interpolator(d3.interpolateInferno)
           .domain(this.getSpectrogramDataDomain())       

       document.getElementById(this.yAxisElementTitleId)?.remove();
       this.chartGroupContainer.append("text")
           .attr("id", this.yAxisElementTitleId)
           .attr("transform", `translate(-30, ${Math.floor(this.height/2)}) rotate(-90) `)
           .html(axisTitles[this.selectedSensor]);

        this.lineGroup.html("");

        this.sensorData.forEach(({psd}, xIndex) => {
            psd.forEach((freq, yIndex) => {
                this.lineGroup.append("rect")
                    .attr("x", this.xScale(xIndex))
                    .attr("y", this.yScale(yIndex))
                    .attr("width", this.xScale.bandwidth())
                    .attr("height", this.yScale.bandwidth())
                    .style("fill", myColor(freq))
            });
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
    getRawDataDomain = () => {
        let domain = this.axis.map(axis => d3.extent(this.sensorData, d => d[axis]))

        return [
            Math.min(...domain.map(axisDomain => axisDomain[0])), // minimum of all axis
            Math.max(...domain.map(axisDomain => axisDomain[1])), // maximum of all axis
        ]
    }

    getSpectrogramDataDomain = () => {
        let domain = this.sensorData.map(item => d3.extent(item.psd))

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
            .attr("stroke-width", this.lineStrokeWidth)
            .attr("d", d3.line()
                .x(d => this.xScale(d.timestamp))
                .y(d => this.yScale(d[axis]))
            )
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