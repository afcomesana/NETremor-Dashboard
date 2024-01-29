import Plotter from "/static/dashboard/Plotter.js";

// Initialize plot class and add event listeners for filters:
const plotter = new Plotter();

const RECORD_TYPE = document.getElementById("record-type").value;


if ( RECORD_TYPE == "ambulatory" ) {

    // Close the other task containers when a different task is selected:
    const taskNamesContainers = Array.from(document.getElementsByClassName("task-name-container"));
    const taskOptionsContainers = Array.from(document.getElementsByClassName("task-options-container"));
    const trialOptions   = Array.from(document.getElementsByClassName("trial-option"));
    
    taskNamesContainers.forEach(task => task.addEventListener("click", () => {
        const taskToExpandId = task.getAttribute("aria-controls");
        taskOptionsContainers.forEach(container => {
            if ( container.id != taskToExpandId ) {
                let collapseInstance = bootstrap.Collapse.getInstance(container);
                collapseInstance?.hide()
            }
        });
    }));
    
    
    trialOptions.forEach(outerOption => {
        outerOption.addEventListener("click", async () => {
            if ( !outerOption.classList.contains("selected") ) {
                trialOptions.forEach(innerOption => {
                    innerOption.classList.remove("selected");
                    innerOption.classList.remove("bg-success");
                    innerOption.classList.add("bg-dark");
                });
                outerOption.classList.add("selected");
                outerOption.classList.add("bg-success");
                outerOption.classList.remove("bg-dark");
    
                await plotter.loadData();
                plotter.renderChart();
            }
    
        });
    });
} else if ( RECORD_TYPE == "continuous" ) {

    document.addEventListener("DOMContentLoaded", async () => {
        await plotter.loadData();
        plotter.renderChart();
    });

    // window.addEventListener("resize")
}

const sensorFilters = Array.from(document.getElementsByClassName("sensor-filter"));
const axisFilters   = Array.from(document.getElementsByClassName("axis-filter"));


sensorFilters.forEach(outerOption => {
    outerOption.addEventListener("click", async () => {
        if ( !outerOption.classList.contains("selected") ) {
            sensorFilters.forEach(innerOption => {
                innerOption.classList.remove("selected");
                innerOption.classList.remove("btn-primary");
            });
            
            outerOption.classList.add("selected");
            outerOption.classList.add("btn-primary");

            await plotter.loadData();
            plotter.renderChart();
        }

    });
});

axisFilters.forEach(axisButton => {

    const axis = axisButton.id.split("-")[1]

    axisButton.addEventListener("click", async () => {
        const axisLine = document.querySelector(`.line.${axis}`);

        if ( axisButton.classList.contains("selected") ) {
            axisButton.classList.remove("selected");
            axisLine?.classList.add("opacity-0");
        } else {
            axisButton.classList.add("selected");
            axisLine?.classList.remove("opacity-0");
        }

        plotter.updateLegend();
        // await plotter.loadData();
        // plotter.renderChart();
    });
});