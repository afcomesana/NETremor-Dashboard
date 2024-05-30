
export const COLOR_CODE = {
    "gyroscope-x": "#3B3486",
    "gyroscope-y": "#7E2553",
    "gyroscope-z": "#80BCBD",
    "accelerometer-x": "#3B3486",
    "accelerometer-y": "#7E2553",
    "accelerometer-z": "#80BCBD",
}

export const AXIS_TITLES = {
    "raw": {
        "accelerometer": "m/s&sup2;",
        "gyroscope": "deg/s"
    },
    "tremor": {
        "accelerometer": "dB",
        "gyroscope": "dB"
    },
}

// ----------------
// DOM ELEMENTS IDS
// ----------------
export const RECORD_CHART_CONTAINER_ID     = "record-chart-container";
export const CHART_GROUP_CONTAINER_ID      = "record-chart-container-group";
export const RECORD_CHART_CONTAINER_SVG_ID = "record-chart-container-svg";
export const RECORD_CHART_LINE_GROUP_ID    = "record-line-group";
export const X_AXIS_ELEMENT_ID             = "chart-x-axis";
export const Y_AXIS_ELEMENT_ID             = "chart-y-axis";
export const Y_AXIS_ELEMENT_TITLE_ID       = "y-axis-title";
export const CHART_GROUP_CLIP_ID           = "chart-group-clip";

// -----------
// CHART SIZES
// -----------
export const MARGIN = {
    top: 10,
    right: 30,
    bottom: 30,
    left: 50
};

export const HEIGHT = 400 - MARGIN.top - MARGIN.bottom;

// ------------
// CHART STYLES
// ------------
export const TRANSITION_MILLIS = 500;
export const LINE_WIDTH = 3;