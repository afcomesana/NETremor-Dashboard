const trialOptions          = Array.from(document.getElementsByClassName("trial-option"));


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