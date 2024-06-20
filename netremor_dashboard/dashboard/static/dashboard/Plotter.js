import {
    COLOR_CODE,
    AXIS_TITLES,
    CHART_GROUP_CONTAINER_ID,
    RECORD_CHART_CONTAINER_ID,
    HEIGHT,
    RECORD_CHART_CONTAINER_SVG_ID,
    MARGIN,
    CHART_GROUP_CLIP_ID,
    X_AXIS_ELEMENT_ID,
    Y_AXIS_ELEMENT_ID,
    Y_AXIS_ELEMENT_TITLE_ID,
    LINE_WIDTH
} from "./constants.js";


export default class Plotter {

    constructor() {

        // -----------------------------------
        // CHART ELEMENT, SIZES AND FEATURES:
        // -----------------------------------
        this.recordChartContainer  = document.getElementById(RECORD_CHART_CONTAINER_ID);
        this.axisElements          = Array.from(document.getElementsByClassName("axis-filter"))
        this.axis                  = this.axisElements.map(axis => axis.id.split("-")[1]);

        // --------------------------
        // CHART FILTERS AND OPTIONS:
        // --------------------------
        this.selectedSensor = null;
        this.selectedPlot   = null;
        this.selectedMetric = null;
        this.timeRange      = false;

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


        // ----------------
        // INITIALIZE CHART
        // ----------------
        this.svg = d3.select(this.recordChartContainer)
            .html(null) // Wipe out anything that could be rendered in the chart's area
            .append("svg")
            .attr("id", RECORD_CHART_CONTAINER_SVG_ID);


        this.zoom = d3.zoom()
            // TODO: Compute the right maximum scaleExtent for the zoom
            .on("zoom", this.handleZoom);
        
        this.svg.call(this.zoom);

        
        this.chartGroupContainer = this.svg.append("g")
            .attr("id", CHART_GROUP_CONTAINER_ID)
            .attr("transform", `translate(${MARGIN.left}, ${MARGIN.top})`);

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
            .attr("id", CHART_GROUP_CLIP_ID)
                .append("svg:rect")
                .attr("x", 0)
                .attr("y", 0);

        
        // Group that will contain the lines
        this.lineGroup = this.chartGroupContainer.append("g")
            .attr("id", "record-line-group")
            .attr("clip-path", `url(#${CHART_GROUP_CLIP_ID})`);

        this.resizeChart();
        // window.addEventListener("resize", this.resizeChart);

    }

    get selectedAxis() {
        return this.axisElements.filter(el => el.classList.contains("selected")).map(el => el.id.split("-")[1]);
    }

    selectAxis(axis) {
        this.axisElements.find(el => el.id == `axis-${axis}`).classList.add("selected");
    }

    resizeChart = async () => {

        this.width = this.recordChartContainer.clientWidth;

        this.svg
            .attr("width", this.width + MARGIN.left + MARGIN.right)
            .attr("height", HEIGHT + MARGIN.top + MARGIN.bottom);

        this.clip
            .attr("width", this.width)
            .attr("height", HEIGHT);

        this.zoom.translateExtent([
            [0, 0],
            [this.width + MARGIN.left + MARGIN.right, HEIGHT + MARGIN.top + MARGIN.bottom]
        ]);

        await this.loadData();
        this.renderChart();
    }

    handleZoom = (event) => {

        clearTimeout(this.zoomTimeout);


        // Rescale X axis:
        this.zoomedXScale = event.transform.rescaleX(this.xScale);
        // this.xAxisElement.call(d3.axisBottom(this.zoomedXScale));

        this.zoomTimeout = setTimeout(async () => {
            this.timeRange = this.zoomedXScale.domain().map(date => new Date(date).getTime());
            await this.loadData();
            this.renderChart();
        }, 150);

        // Redraw present lines:
        this.renderChart();
        // const data = this.data.map(item => new Object({"timestamp": item.timestamp, "x": item.x_amplitude, "y": item.y_amplitude, "z": item.z_amplitude}));
        // this.drawLines(data, newXScale)

    }



    getPlotOptions = () => {

        // Get selected option, sensor and axis
        const selectSensorElement = document.querySelector(".sensor-filter.selected");
        const selectMetricElement = document.querySelector(".metric-option.selected");

        if ( !selectSensorElement ) {
            throw "No sensor selected.";
        }

        if ( !selectMetricElement ) {
            throw "No metric selected.";
        }


        const selectedSensor = selectSensorElement.id.split("-")[1];
        const selectedMetric = selectMetricElement.id.split("-")[1];

        // If trial, sensor or metric is changed with respect to the previous set of options, we must update the overall data:
        const updateAllTimeData = (!this.selectedSensor || selectedSensor != this.selectedSensor)
                                || (!this.selectedMetric || selectedMetric != this.selectedMetric);

        this.selectedSensor = selectedSensor;
        this.selectedMetric = selectedMetric;

        return updateAllTimeData;
    }
    
    parseTremorToStandarFormat = (data, key) => data.map(chunk => chunk.map(item => new Object({"timestamp": item.timestamp, "x": item[`x_${key}`], "y": item[`y_${key}`], "z": item[`z_${key}`]})));

    loadData = async () => {

        const updateAllTimeData = this.getPlotOptions();

        this.showSpinner(`#${RECORD_CHART_CONTAINER_ID}`);

        let response;

        try {
            response = await this.fetchData({
                sensor: this.selectedSensor,
                metric: this.selectedMetric,
                samples: this.width,
                timeRange: this.timeRange
            });
    
        } catch(error) {
            console.warn(error);
        }

        if ( !response ) return;

        const { data, limits, step } = response;
        
        this.data = data;
        
        // Parse data to have the simple named axis
        if ( this.selectedMetric == "tremor" ) {
            this.frequencies = this.parseTremorToStandarFormat(this.data, "frequency");
            this.data        = this.parseTremorToStandarFormat(this.data, "amplitude");
        }

        // First time that this sensor data is loaded:
        if ( updateAllTimeData ) {

            // If we are applying zoom, we need to fetch the data outside of the zoom so that we can pan and zoom out            
            if ( this.timeRange ) {

                let { data: allTimeData, limits: allTimeLimits, step: allTimeStep } = await this.fetchData({
                    sensor: this.selectedSensor,
                    metric: this.selectedMetric,
                    samples: this.width,
                    timeRange: false
                });
                
                if (this.selectedMetric == "tremor") {
                    allTimeData = this.parseTremorToStandarFormat(allTimeData, "amplitude")
                }

                this.allTimeData = allTimeData;
                this.limits = allTimeLimits;
                this.zoom.scaleExtent([1,allTimeStep]);

            } else {
                this.allTimeData   = this.data;
                this.limits        = limits;
                this.zoom.scaleExtent([1,step]);
            }

            if (this.allTimeData.length == 0) {
                this.renderErrorMessage("No data was found.");
                return;
            }

            // SELECT THE AXIS THAT HAS THE MOST TREMOR ENERGY
            if (this.selectedAxis.length == 0) {
                let axisToSelect,
                    currentMean = -Infinity,
                    dataLength = this.data.flat().length;

                this.axis.forEach(axis => {
                    const axisMean = this.data.flat().reduce((acc, item) => acc + item[axis], 0) / dataLength;
                    if (axisMean > currentMean) {
                        axisToSelect = axis;
                        currentMean = axisMean;
                    }
                });

                this.selectAxis(axisToSelect);
            }

        // There is already data loaded (zoom):
        } else if (this.data.length > 0) {

            const firstDataTimestamp = this.data.flat()[0].timestamp,
                lastDataTimestamp    = this.data.flat().slice(-1)[0].timestamp,
                allTimeDataChunk     = this.allTimeData.flat().filter(item => item.timestamp < firstDataTimestamp || item.timestamp > lastDataTimestamp);


            const sortedData = this.data.concat(allTimeDataChunk).flat().sort((a, b) => a.timestamp - b.timestamp);
            this.data        = [];
            let dataIndex    = 0,
                dataItem     = sortedData[dataIndex];

            this.limits.forEach(limit => {

                if (!dataItem) return;

                const currentChunk = [];

                while( dataItem && dataItem.timestamp <= limit.final_timestamp ) {

                    const lastItem = currentChunk.slice(-1)[0];

                    if (!lastItem || dataItem.timestamp != lastItem.timestamp) {
                        currentChunk.push(dataItem);
                    }

                    dataItem = sortedData[++dataIndex];
                }

                if (currentChunk.length) {
                    // Apply mean
                    this.data.push(currentChunk);
                }
            });

        }

        this.hideSpinner();
    }

    fetchData = async params => {

        const CRSF_TOKEN = this.getCsrfToken();

        try {
            // TODO: Take into account the width of the chart container:
            const response = await fetch(window.location.pathname, {
                method: "POST",
                headers: {"X-CSRFToken": CRSF_TOKEN, "Content-type": "application/json"},
                body: JSON.stringify(params)
            })

            if ( !response.ok ) {
                this.renderErrorMessage(`Error fetching data: ${await response.text()}`);
                return;
            }

            return await response.json();

        } catch(error) {
            console.error(`Error fetching data: ${error}`);
            this.renderErrorMessage(`Could not load data to plot the chart.`)
        }
    }

    renderChart = () => {

        if (!this.data || this.data.lenth == 0) {
            console.warn("No data available.");
            return;
        }

        this.plot(AXIS_TITLES[this.selectedMetric][this.selectedSensor]);
    }

    setXAxis = () => {

        // Axis scale (function to parse values to positions in axis):
        if (!this.zoomedXScale) {
            this.xScale = d3.scaleTime()
                .domain(d3.extent(this.data.flat(), item => new Date(item.timestamp)))
                .range([0, this.width]);
        }

        document.getElementById(X_AXIS_ELEMENT_ID)?.remove()

        this.xAxisElement  = this.chartGroupContainer.append("g")
            .attr("id", X_AXIS_ELEMENT_ID)
            .attr("transform", `translate(0, ${HEIGHT - MARGIN.bottom + MARGIN.top})`)
            .call(d3.axisBottom(this.zoomedXScale || this.xScale));
    }

    setYAxis = (domain, yAxisTitle) => {

        const chartVerticalMargin = 20;

        this.yScale = d3.scaleLinear()
            .domain(domain)
            .range([HEIGHT- chartVerticalMargin, chartVerticalMargin]);

        document.getElementById(Y_AXIS_ELEMENT_ID)?.remove();

        this.yAxisElement = this.chartGroupContainer.append("g")
            .attr("id", Y_AXIS_ELEMENT_ID)
            .call(d3.axisLeft(this.yScale));

        document.getElementById(Y_AXIS_ELEMENT_TITLE_ID)?.remove();

        this.chartGroupContainer.append("text")
            .attr("id", Y_AXIS_ELEMENT_TITLE_ID)
            .attr("transform", `translate(-30, ${Math.floor(HEIGHT/2)}) rotate(-90) `)
            .html(yAxisTitle);
    }

    plot = axisTitle => {
        this.setXAxis();

        this.setYAxis(this.getDataDomain(), axisTitle);

        this.drawLines();
    }

    /**
     * 
     * @param {Array} axis - array with all the selected axis by the user
     * @returns {Array} being the first element the minimum value along all the axis and the
     * second element the maximum value along all the axis
     */
    getDataDomain = () => {
        let domain = this.axis.map(axis => d3.extent(this.data.flat(), d => d[axis]))

        return [
            Math.min(...domain.map(axisDomain => axisDomain[0])), // minimum of all axis
            Math.max(...domain.map(axisDomain => axisDomain[1])), // maximum of all axis
        ]
    }

    drawLines = () => {

        const xScale = this.zoomedXScale || this.xScale;

        // Remove any lines that may be currently plotted:
        Array.from(this.recordChartContainer.getElementsByClassName("line")).forEach(line => line.remove());

        this.axis.forEach(axis => {

            this.data.forEach((chunk, index) => {

                const lineId    = `${this.selectedSensor}-${axis}-line-${index}`;
                const lineClass = `line ${this.selectedSensor} ${axis} ${this.selectedAxis.includes(axis) ? "" : "opacity-0"}`;

                if ( chunk.length > 1 ) {
                    this.lineGroup.append("path")
                        .datum(chunk)
                        .attr("id", lineId)
                        .attr("class", lineClass)
                        .attr("fill", "none")
                        .attr("stroke", COLOR_CODE[`${this.selectedSensor}-${axis}`])
                        .attr("stroke-width", LINE_WIDTH)
                        .attr("d", d3.line()
                            .x(d => xScale(d.timestamp))
                            .y(d => this.yScale(d[axis]))
                        )
                } else {
                    this.lineGroup.append("circle")
                        .attr("id", lineId)
                        .attr("class", lineClass)
                        .attr("cx", xScale(chunk[0].timestamp))
                        .attr("cy", this.yScale(chunk[0][axis]))
                        .attr("r", LINE_WIDTH*0.8)
                        .style("fill", COLOR_CODE[`${this.selectedSensor}-${axis}`])
                }
            });
        });
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

    getCsrfToken = () => {
        // CSRF token to make the request
        let csrfToken = document.cookie.split(";").find(cookie => cookie.includes("csrftoken"));
        if ( !csrfToken ) {
            // Show error message
            throw "No csrf token";
        }

        return csrfToken.split("=")[1];
    }

    renderErrorMessage = (message, icon = null) => {
        this.recordChartContainer.innerHTML = `
            <div class="alert alert-danger">${message}</div>
        `
    }

    selectAxis = (axisName, select = true) => {
        const axisButton = this.axisElements.find(el => el.id == `axis-${axisName}`);

        if (select) {
            axisButton.classList.add("selected")
        } else {
            axisButton.classList.remove("selected")
        }

        axisButton.style.background = select ? COLOR_CODE[`${this.selectedSensor}-${axisName}`] : "none";
        axisButton.style.color      = select ? "white" : "black";
    }

    updatePlotAxis = async event => {

        const axisButton = event.target.closest(".axis-filter");
        const axisName   = axisButton.id.split("-")[1];

        this.selectAxis(axisName, !this.selectedAxis.includes(axisName));

        this.renderChart();

        // const axisLine   = document.querySelector(`.line.${axisName}`);

        // if ( axisButton.classList.contains("selected") ) {
        //     axisButton.classList.remove("selected");
        //     axisLine?.classList.add("opacity-0");
            
        //     axisButton.style.background = "none";
        //     axisButton.style.color = "black";
        // } else {
        //     axisButton.classList.add("selected");
        //     axisLine?.classList.remove("opacity-0");

        //     axisButton.style.background = COLOR_CODE[`${this.selectedSensor}-${axisName}`];
        //     axisButton.style.color = "white";
        // }
    }
}


// -----------------------------
// AMBULATORY RECORD PLOTTER
// -----------------------------
/*
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

const trialOption    = document.querySelector(".trial-option.selected");
this.trialOption    = null;


        // const selectedPlot = [this.selectedMetric, this.selectedSensor, this.timeRange].join("-");
        // if ( selectedPlot != this.selectedPlot ) {

        // this.selectedPlot = selectedPlot;


*/