# NETremor Dashboard

## What This Repository Is

This repository contains a Django-based data platform for receiving, normalizing, storing, processing, and visualizing inertial sensor recordings collected during experiments in which human subjects perform daily activities. The codebase is not a full end-to-end machine learning training system by itself; instead, it plays the role that many activity-recognition projects urgently need before modeling can be reliable:

- a structured ingestion layer for experimental recordings,
- a database schema that preserves subject metadata and behavioral labels,
- a preprocessing pipeline that turns heterogeneous raw files into a compact queryable format,
- a signal-processing layer that derives tremor-oriented representations,
- and an authenticated dashboard for exploring recordings and downloading curated datasets.

That makes this project especially valuable for work on activity prediction from inertial data because the hard part in those projects is often not only the classifier, but the data engineering around the classifier:

- making sure timestamps are ordered,
- keeping accelerometer and gyroscope data identifiable,
- attaching trials/tasks/positions to the right signal segments,
- handling discontinuities and duplicated uploads,
- sampling long recordings fast enough for visualization,
- and exporting data in a form that can later feed feature engineering or model training.

In other words, this repository is best understood as the operational data backbone around an inertial-sensing research workflow.

---

## Why This Matters For Activity Prediction From IMU Data

If the broader project goal is to predict activities of daily living from inertial sensors, this repository contributes technical value in several concrete ways:

### 1. It turns experimental recordings into a labeled signal corpus

The database does not only store files. It stores:

- who the subject is,
- what type of recording was collected,
- which task or position each file or time segment belongs to,
- what sensor produced the signal,
- and what the temporal extent of each file is.

That is the difference between "a folder full of CSVs" and "a dataset suitable for supervised learning."

### 2. It preserves the segmentation information needed for supervised learning

Human activity recognition depends on labels. This project stores labels at two complementary granularities:

- **Ambulatory recordings**: a recording is naturally organized into task/trial units.
- **Continuous recordings**: task and position labels are stored as temporal intervals (`starts_at`, `ends_at`) over long streams.

That is exactly the sort of annotation structure required to create windows for training or evaluation later.

### 3. It normalizes irregular raw sensor streams

Raw mobile/wearable data is rarely perfectly sampled. This repository explicitly handles:

- unsorted timestamps,
- small timestamp gaps,
- large discontinuities,
- overlapping continuous uploads,
- and inconsistent file chunking caused by acquisition constraints.

Those are practical data-quality problems that directly affect downstream model quality if ignored.

### 4. It introduces a compact intermediate format optimized for repeated reading

Instead of repeatedly scanning CSV text files, the project converts data to custom binary `.imu` files and derived `.tr` tremor files. This is important because visualization and later analytical jobs often need:

- windowed reads,
- decimated reads,
- fast random access by timestamp range,
- and lower I/O overhead than text CSV can provide.

### 5. It supports human-in-the-loop quality control

Before training any classifier, researchers usually need to visually inspect recordings. The dashboard provides:

- per-subject browsing,
- per-record navigation,
- sensor selection,
- axis selection,
- raw vs tremor views,
- zoom-driven refetching,
- and export of curated record bundles.

That helps researchers validate signal integrity, temporal continuity, and annotation quality before committing to model-building decisions.

### 6. It already contains one example of derived clinical analytics

The code computes a bradykinesia probability estimate from accelerometer recordings. Even though that is not a general activity classifier, it shows the architectural pattern for attaching secondary analytics to the ingestion pipeline:

1. ingest raw signal,
2. normalize it,
3. compute a derived metric,
4. store the result per subject,
5. surface it in the dashboard.

That same pattern could later be reused for:

- activity classification scores,
- gait quality scores,
- freezing episodes,
- tremor burden,
- posture transitions,
- or anomaly detection outputs.

---

## High-Level Architecture

At a high level, the repository is split into three main concerns:

1. **Data ingestion and processing** in `endpoint/`
2. **Authenticated dashboard and plotting UI** in `dashboard/`
3. **Shared utilities and custom file formats** in `utils.py` and `imu.py`

There is also a small `mailproxy/` module that acts as a lightweight email-sending endpoint.

### End-to-end flow

```text
Acquisition client / experiment app
        |
        |  POST /endpoint/<record_type>/  + files + body.json + API key
        v
endpoint.views.save_record
        |
        |-- save/update subject metadata
        |-- store tasks and positions
        |-- save raw CSV files
        |-- create relational metadata records
        v
endpoint.utils.process_record_datafiles (background)
        |
        |-- sort CSV by timestamp
        |-- convert CSV -> .imu
        |-- split on large gaps
        |-- interpolate across small gaps
        |-- compute tremor -> .tr
        |-- update file timestamp ranges in DB
        |-- optionally compute bradykinesia
        v
MySQL + raw files + processed binary files
        |
        |  GET /record/<id>/         -> HTML page
        |  POST /record/<id>/        -> windowed chart data
        |  GET /record/<id>?download -> export bundle
        v
Dashboard frontend (D3 + Bootstrap)
```

---

## Repository Structure

```text
netremor_dashboard/
├── manage.py
├── netremor_dashboard/        # Django project settings and root URLs
├── endpoint/                  # Upload API, preprocessing, data models for signal domain
├── dashboard/                 # Authenticated UI, templates, chart logic
├── mailproxy/                 # Auxiliary email proxy endpoint
├── imu.py                     # Custom binary IMU/tremor file format read/write logic
├── utils.py                   # Shared utilities (logging, random strings, email, text normalization)
├── assess-data.py             # Manual data quality helper script for timestamp gaps
├── test.py                    # Standalone helper for CSV sorting experimentation
└── readme.md                  # This file
```

### Important directories expected by settings

The application expects these directories relative to the project root:

- `data-files/` for raw uploaded CSV files
- `imu-files/` for compact binary IMU files
- `tremor-files/` for derived tremor files
- `log/` for log output

They are defined in `netremor_dashboard/settings.py`.

### Technology stack

The implementation clearly depends on the following core technologies:

- Python
- Django 4.2
- MySQL
- NumPy
- SciPy
- Pandas
- `python-dotenv`
- `pytz`
- D3.js
- Bootstrap
- Font Awesome

From an architectural point of view, that combination makes sense:

- Django handles authentication, routing, templating, and ORM access,
- MySQL stores the normalized experimental metadata,
- NumPy/SciPy/Pandas handle signal and tabular processing,
- and D3 provides the custom interactive visualization layer needed for time-series exploration.

---

## Django Application Architecture

## `netremor_dashboard/`

This is the Django project shell:

- `settings.py` defines database settings, static configuration, upload limits, sensor choices, and default signal-processing constants.
- `urls.py` mounts three URL groups:
  - `/` -> `dashboard.urls`
  - `/endpoint/` -> `endpoint.urls`
  - `/mailproxy/` -> `mailproxy.urls`

## `endpoint/`

This is the backend ingestion and signal-processing domain.

Its responsibilities are:

- receiving uploaded recordings,
- validating API-key access,
- persisting subject/task/position metadata,
- saving uploaded files,
- building database relations,
- converting raw data into custom formats,
- computing tremor features,
- and generating derived bradykinesia values.

Core files:

- `endpoint/models.py`: signal-domain relational schema
- `endpoint/views.py`: upload API entry point
- `endpoint/utils.py`: most of the ingestion and processing logic
- `endpoint/signal_processing.py`: small filtering helper
- `endpoint/management/commands/`: cron/manual processing commands

## `dashboard/`

This is the user-facing application.

Its responsibilities are:

- authentication and registration,
- verification emails,
- listing subjects,
- listing records per subject,
- loading chart data on demand,
- and bundling exports.

Core files:

- `dashboard/views.py`: HTML pages + chart-data endpoints
- `dashboard/utils.py`: login helpers, email helpers, and chart-data extraction helpers
- `dashboard/templates/dashboard/*.html`: page layout
- `dashboard/static/dashboard/Plotter.js`: main D3 plotting engine
- `dashboard/static/dashboard/record.js`: UI event wiring for record pages
- `dashboard/static/dashboard/constants.js`: plotting colors, IDs, layout constants

## `mailproxy/`

This module exposes a small POST endpoint for sending mail through local SMTP if the correct API key is supplied. It is not central to the sensor-processing pipeline, but can be used to send alerts or notifications to patients,
developers, clinicians or researchers. The reason that it is exposed is
because requests from Android phones or charge-bases for custom devices
can access this endpoint to send notification regarding those devices (for
example: a subject hasn't uploaded any record in the last 24 hours).

---

## Database Architecture

The database uses MySQL and a normalized relational schema. This is a very sensible choice for this domain because inertial-data projects typically need repeated many-to-one and many-to-many style queries:

- subjects to records,
- records to files,
- files to sensors,
- files to tasks,
- files to positions,
- and subjects to derived metrics.

The test code in `endpoint/tests.py` is especially revealing here: it compares relational queries against a denormalized Mongo-style structure. This is because project evolved with explicit awareness of database design tradeoffs and intentionally chose relational normalization for this workload.

## Entity summary

| Model | Purpose |
| --- | --- |
| `Subject` | Person-level metadata for an experimental subject |
| `Record` | A recording session for a subject |
| `Datafile` | Raw uploaded sensor file plus parsing metadata |
| `Imufile` | Compact binary representation derived from a raw file |
| `Tremor_file` | Derived tremor representation computed from an IMU file |
| `Task` | Catalog of behavioral/experimental tasks |
| `Position` | Catalog of subject positions/postures |
| `Datafile_task_rel` | Links tasks to files/records, with trial or time bounds |
| `Datafile_position_rel` | Links positions to files/records, with time bounds |
| `Bradykinesia` | Derived per-subject bradykinesia probability |
| `Verification` | User-account verification status for dashboard access |

## Schema details

### `Subject`

This model stores subject metadata:

- `id`: external string identifier, primary key
- `name`
- `gender`
- `birth_year`
- `illness_start_year`
- `dominant_hand`
- `diagnosis`

Why this matters:

- it preserves clinically relevant covariates,
- it allows stratification later,
- and it keeps subject identity stable across multiple records.

The `age()` helper is derived from `birth_year`.

### `Record`

This model represents a recording session belonging to one subject.

Fields:

- `subject`
- `type` in `{ambulatory, continuous, finger_tap}`
- `added_on`
- `is_being_processed`

Interpretation:

- **Ambulatory** records are organized around discrete tasks/trials.
- **Continuous** records are long streams with labeled intervals inside them.
- **Finger tap** a type of record that was never implemented during the project.

### `Datafile`

This is the core metadata record for each uploaded raw signal file.

Fields:

- `record`: owning record
- `name`: stored filename
- `sensor`: `accelerometer` or `gyroscope`
- `delta_t`: expected sample interval in milliseconds
- `timestamp_threshold`: maximum tolerated gap before splitting into a new IMU file
- `timestamp_colname`: which CSV column is treated as timestamp
- `initial_timestamp`
- `final_timestamp`
- `separator`
- `is_processed`

This model is important because it bridges the physical file on disk and the semantic object in the database.

### `Imufile`

Each `Imufile` is a processed binary version of a `Datafile`.

Fields:

- `record`
- `datafile`
- `name`
- `sensor`
- `initial_timestamp`
- `final_timestamp`

Why this is useful:

- one raw file can produce one or more IMU files,
- especially when large timestamp gaps force splitting,
- and the stored timestamp range lets the dashboard locate the right chunks without scanning every file.

### `Tremor_file`

This model mirrors `Imufile`, but for tremor-derived output rather than raw re-encoding.

It exists because tremor data has different semantics from raw tri-axial data:

- its time step is analysis-window-based rather than raw-sample-based,
- and each sample contains dominant frequency and amplitude pairs rather than raw x/y/z acceleration or angular velocity.

### `Task`

This is a shared lookup table for experimental tasks:

- `id`
- `name`
- `description`

This is a strong design decision. Instead of embedding task labels repeatedly in uploaded bodies or filenames, the system canonicalizes tasks into a table. That reduces drift in naming and makes downstream querying more consistent.

### `Position`

Same idea as `Task`, but for posture/position annotations.

This is especially useful for continuous monitoring datasets where activity alone is not enough and posture context matters.

### `Datafile_task_rel`

This relation table is one of the most important parts of the schema.

It links:

- a `Record`
- a `Datafile`
- and a `Task`

Additional fields:

- `trial` for ambulatory trial indexing
- `starts_at`
- `ends_at`

This lets the same table support two labeling strategies:

- **trial-based labeling** for ambulatory data
- **interval-based labeling** for continuous data

That is a compact and practical schema design for mixed experimental paradigms.

### `Datafile_position_rel`

This is the posture/position analog to `Datafile_task_rel`.

It supports:

- which position applies to which file
- and when, within a long continuous recording, that position starts and ends

### `Bradykinesia`

Stores:

- `subject`
- `probability`
- `added_on`

This is an example of how derived analytics are attached to the subject level rather than to a single file.

### `Verification`

This belongs to the dashboard authentication layer rather than the signal domain:

- `user`
- `code`
- `is_verified`

It controls whether a registered dashboard user can log in.

## Relationship overview

```text
Subject
  ├── Record (1:N)
  │     ├── Datafile (1:N)
  │     │     ├── Imufile (1:N in practice after gap splitting)
  │     │     └── Tremor_file (1:N matching processed IMU outputs)
  │     ├── Datafile_task_rel (1:N)
  │     └── Datafile_position_rel (1:N)
  └── Bradykinesia (1:N over time, though often used as latest-per-subject)

Task <── Datafile_task_rel ──> Datafile
Position <── Datafile_position_rel ──> Datafile
```

## Why the database design is technically strong

For an activity-prediction project, this schema has several advantages:

- it separates identity, recording session, file metadata, and labels cleanly,
- it supports both segmented and continuous acquisition protocols,
- it keeps sensor files queryable by time span,
- it avoids duplicating task definitions across uploads,
- and it preserves the exact experimental context needed to later build windowed training datasets.

---

## Ingestion API Architecture

The upload entry point is `endpoint.views.save_record`, mounted at:

- `/endpoint/ambulatory/`
- `/endpoint/continuous/`

The route itself determines which save function is called.

## Request security

Uploads require a custom API key:

- the code reads the value from `request.META["HTTP_NETREMOR_API_KEY"]`
- the secret is loaded from environment variables via `dotenv`

This makes the endpoint suitable for machine-to-machine ingestion from a mobile app, wearable gateway, or experiment collection service.

## Multipart payload contract

The code expects multipart form data containing:

- one special file named `body.json`
- plus one or more uploaded sensor files

`body.json` contains the structured metadata for the upload.

### Required/expected `body.json` fields

At minimum, the code clearly expects:

- `subject_id`
- `record_added_on` in Unix epoch milliseconds

It also supports subject metadata such as:

- `name`
- `gender`
- `birth_year`
- `illness_start_year`
- `dominant_hand`
- `diagnosis`

Optional record-processing metadata:

- `delta_t`

Optional labeling arrays:

- `recorded_tasks`
- `recorded_positions`

### Typical `body.json` shape

The repository does not include a formal API spec, but the implementation strongly implies a payload like this:

```json
{
  "subject_id": "subject-001",
  "name": "Example Subject",
  "gender": "female",
  "birth_year": 1958,
  "illness_start_year": 2017,
  "dominant_hand": "right",
  "diagnosis": "parkinson",
  "record_added_on": 1718628117678,
  "delta_t": 30,
  "recorded_tasks": [
    {
      "task_id": "WALK",
      "task_name": "Walk",
      "task_description": "Normal walking",
      "trial": 0,
      "accelerometer_filename": "walk-acc.csv",
      "gyroscope_filename": "walk-gyr.csv",
      "starts_at": 1718628117678,
      "ends_at": 1718628177678
    }
  ],
  "recorded_positions": [
    {
      "position_id": "STAND",
      "position_name": "Standing",
      "position_description": "Standing upright",
      "starts_at": 1718628117678,
      "ends_at": 1718628177678
    }
  ]
}
```

Not every field is required in every mode, but this shows the intended structure.

---

## Two Recording Modes

## 1. Ambulatory mode

Ambulatory recordings are modeled as task-oriented recordings with trials.

The logic is:

1. create a new `Record(type="ambulatory")`,
2. iterate through declared tasks,
3. for each task, look for per-sensor files such as accelerometer and gyroscope,
4. save each file as a `Datafile`,
5. create `Datafile_task_rel` entries including `trial`,
6. asynchronously process the stored data.

This mode is useful when the experimental design is naturally segmented, for example:

- walking trial 1,
- sit-to-stand trial 2,
- hand movement trial 3.

That structure is very close to how supervised training sets are often created.

## 2. Continuous mode

Continuous recordings are modeled as long streams that may arrive as multiple file chunks.

The logic is:

1. create or reuse one `Record(type="continuous")` for the subject,
2. identify each file's sensor by filename,
3. convert `.dat` or `.txt` extensions to `.csv`,
4. trim overlapped timestamps against already-stored files of the same sensor,
5. create a `Datafile`,
6. attach task and position intervals to that file,
7. asynchronously process the raw file into faster formats.

This mode is ideal for real-world or semi-naturalistic monitoring, where later classification requires:

- long time context,
- interval annotations,
- and progressive upload of recording chunks.

---

## Raw File Handling And Quality Controls

This project performs several useful data-quality operations before visualization.

## Timestamp sorting

Before converting a raw CSV to binary, `process_record_datafiles()` calls `sort_csv_file()` on every pending `Datafile`.

That function:

1. reads the CSV header,
2. finds the timestamp column index,
3. copies the body to a temporary file,
4. calls Unix `sort -n` on the timestamp field,
5. writes the sorted body back under the original header.

Why this matters:

- mobile/wearable exports are not always guaranteed to be ordered,
- and interpolation or decimation logic becomes unsafe if timestamps go backward.

## Overlap removal for continuous uploads

`save_continuous_record()` includes custom logic to avoid storing duplicated samples when a new uploaded file overlaps with already stored files of the same sensor.

The algorithm is:

1. inspect the first timestamp of the new file,
2. find previously stored datafiles whose `final_timestamp` exceeds that timestamp,
3. rewrite the incoming file into a temporary "no-overlap" version,
4. keep only rows whose timestamps fall outside existing file ranges,
5. replace the original saved file with the trimmed version.

This is a practical and very valuable feature for longitudinal sensing systems where uploads may be retried or partially overlapping.

## Small-gap interpolation vs large-gap splitting

The custom IMU conversion logic distinguishes between:

- **small gaps**, where interpolation is acceptable,
- and **large gaps**, where the stream should be split into different files.

This is one of the most important implementation details in the repository and deserves close attention.

---

## Custom Sensor Data Formatting

This is one of the most distinctive technical parts of the project.

The raw uploaded sensor files remain on disk as CSV, but for efficient repeated reading the code transforms them into a custom binary format using `imu.py`.

There are two custom formats:

- `.imu` for normalized raw sensor streams
- `.tr` for derived tremor summaries

## Why the project does not rely only on CSV

CSV is portable, but it is not ideal for interactive exploration of long inertial streams because:

- it repeats the timestamp on every row,
- it is expensive to scan for every visualization request,
- it is text-based and larger than binary storage,
- it is awkward for fast decimation,
- and it does not intrinsically encode signal continuity assumptions.

The custom binary layer addresses those issues.

---

## The `.imu` format in detail

The `.imu` format is created by `imu.wimu()`.

### Conceptual idea

Instead of storing:

```text
timestamp,x,y,z
1718628117678,0.11,-0.03,9.79
1718628117708,0.09,-0.05,9.81
1718628117738,0.10,-0.04,9.80
...
```

the format stores:

1. a compact header containing the sample interval and first timestamp,
2. one list of sanitized column names,
3. then only the numeric sample values as packed 32-bit floats.

The timestamp for each sample is reconstructed as:

```text
timestamp = initial_timestamp + sample_index * delta_t
```

That works because the format assumes quasi-regular sampling after normalization.

### Exact header fields

The IMU header contains:

1. `delta_t` as unsigned short integer, big-endian, 2 bytes
2. `initial_timestamp` as unsigned long long, big-endian, 8 bytes
3. `columns` as a null-terminated UTF-8 byte string

Important details:

- column names are taken from the CSV header,
- the timestamp column is removed,
- remaining column names are lowercased,
- then stripped down to ASCII lowercase letters only,
- and joined by commas before appending the terminating `\0` byte.

That means original names like `X`, `Accel X`, or `x` would all collapse toward simplified lowercase ASCII labels.

### Body layout

Each body row stores the non-timestamp numeric values as 32-bit floats.

For a tri-axial signal with columns `x,y,z`, each sample uses:

- 3 values x 4 bytes = 12 bytes per sample

The body is therefore fixed-width once the column count is known from the header.

### Behavioral normalization performed during write

The `.imu` writer re-encode bytes and imposes a temporal interpretation on the signal.

#### A. Gap detection

For each row, the writer compares the new timestamp to the previous timestamp.

It computes:

```text
gap = timestamp - last_timestamp
```

#### B. Missing-time accumulation

It tracks:

```text
missing_time += gap - delta_t
```

This lets the writer reason about how far the real timestamps deviate from the expected regular cadence.

#### C. Large-gap splitting

If `gap > timestamp_threshold`, the current `.imu` file is closed and a new `.imu` file is started because:

- a large temporal discontinuity usually means a real interruption in recording,
- pretending it is continuous would distort any later visualization or temporal analysis,
- especially when downstream code reconstructs timestamps from `delta_t`.

This is how one `Datafile` can legitimately produce multiple `Imufile` records.

#### D. Small-gap interpolation

If the accumulated missing time exceeds one nominal `delta_t`, the writer inserts interpolated samples between the previous and current real samples.

Interpolation is linear per channel:

```text
interpolated_value =
  last_value + ((value - last_value) / interpolation_samples_amount) * interpolation_index
```

Why this is helpful:

- slight irregularities are common in wearable sensing,
- small interpolation keeps the binary stream approximately uniform,
- and that greatly simplifies later random access and downsampling.

#### E. Drift control

After interpolation, the writer reduces `missing_time` modulo `delta_t`.

That prevents interpolation drift from accumulating without bound.

### Resulting design tradeoff

The custom `.imu` format is not a raw archival mirror of the source CSV. It is an intentionally normalized working format optimized for:

- interactive reads,
- approximate regular sampling,
- compactness,
- and downstream signal processing.

That is a very reasonable tradeoff for research and dashboard usage, as long as the raw CSV is still preserved, which this project does.

---

## Reading `.imu` files efficiently

The corresponding reader is `imu.rimu()`, which delegates to `read_custom_formatted_file()`.

This function is important because it explains how the dashboard can zoom into long recordings without loading everything.

### How the reader works

1. Read the fixed-size header fields.
2. Read the null-terminated column string.
3. Determine bytes per sample from the number of columns.
4. Compute total sample count from file size.
5. Derive the final timestamp from:

```text
final_timestamp = initial_timestamp + total_samples * delta_t
```

6. Convert requested timestamp bounds into byte offsets.
7. Seek into the file.
8. Read only every `step`-th sample if decimation is requested.

### Why this is valuable

Because samples are fixed-width and timestamps are reconstructable, the system can jump to the relevant region without scanning the whole file line by line. That is exactly the kind of access pattern you want when rendering a chart over a selected time interval.

### `n_samples` support

The reader can receive a target `n_samples`. In that case it computes a decimation step as:

```text
step = floor(samples_in_time_range / n_samples)
```

bounded below by 1.

This is a straightforward but effective way to return approximately screen-resolution-sized data rather than full raw data.

---

## The `.tr` tremor format in detail

The tremor format is created by `imu.wtremor()`.

It is not simply another copy of the raw signal. It stores a derived time series where each sample represents a tremor analysis window.

### What the tremor pipeline computes

For each axis of an IMU file:

1. apply a band-pass filter,
2. run a short-time Fourier transform,
3. find the dominant frequency bin for each time frame,
4. keep the dominant frequency and corresponding amplitude,
5. write those results into a custom binary file.

So each time frame does not store x/y/z raw kinematics. It stores:

- `x_frequency`, `x_amplitude`
- `y_frequency`, `y_amplitude`
- `z_frequency`, `z_amplitude`

### Tremor header fields

The tremor header contains:

1. `delta_t` as float32: time step between successive analysis frames in milliseconds
2. `initial_t` as float32: analysis-window start offset, which may be negative because of FFT padding
3. `initial_timestamp` as unsigned long long
4. `first_no_padding_sample` as unsigned long long
5. `last_no_padding_sample` as unsigned long long
6. `columns` as a null-terminated string

This is richer than the `.imu` header because spectral analysis has padding/border semantics that raw streams do not.

### Tremor body layout

The body stores float pairs. For each analysis frame and each axis, the code writes:

- dominant frequency
- dominant amplitude

packed as 32-bit floats.

### Signal-processing parameters used

Defaults are pulled from settings for the background pipeline:

- low pass: `2 Hz`
- high pass: `10 Hz`
- hop size: `1 second`
- window size: `3 seconds`

Inside `wtremor()`:

- sampling frequency is derived from IMU `delta_t`
- Gaussian windows are used
- oversampling factor is 16
- SciPy `ShortTimeFFT` is used with PSD scaling

### Why this derived format is useful

For activity analysis and movement disorder analysis, raw time series alone are not always the most interpretable representation. A compact tremor representation:

- surfaces rhythmic behavior,
- makes dominant movement frequency explicit,
- and is much lighter to browse visually than a full spectrogram tensor.

Even if the future ML model is not a tremor classifier, this kind of derived view is very helpful for exploratory analysis and clinical quality control.

---

## Background Processing Pipeline

The heart of backend processing is `endpoint.utils.process_record_datafiles(record)`.

This function does three major things:

1. sort pending raw files,
2. convert them to IMU format,
3. compute tremor files.

It also triggers bradykinesia computation in a separate thread.

## Detailed sequence

### Step 1. Guard against duplicate processing

If `record.is_being_processed` is already true, the function exits. Otherwise it marks the record as being processed.

This is a simple but important concurrency guard.

### Step 2. Sort CSV data

Pending `Datafile` rows are collected with `is_processed=False`, then each raw CSV is sorted by timestamp.

### Step 3. Compute bradykinesia asynchronously

The code launches:

```text
threading.Thread(compute_bradykinesia, args=[record.subject_id]).start()
```

This means the subject-level metric is conceptually part of the same ingestion lifecycle, but decoupled enough not to block file conversion.

### Step 4. Convert CSV to `.imu`

For each pending raw `Datafile`, the code passes:

- `delta_t`
- `timestamp_threshold`
- `timestamp_colname`
- `separator`

to `imu.wimu()`.

This is important architecturally because it means the conversion behavior is stored as metadata on each raw file, not hard-coded globally.

### Step 5. Persist `Imufile` metadata

After writing the binary files, the code reads each processed file just enough to determine its timestamp range and creates an `Imufile` row.

Then it updates the parent `Datafile` with:

- `initial_timestamp`
- `final_timestamp`

using the aggregate min/max of all derived IMU chunks.

That lets one raw file represent a wider logical timespan even if internally split into several processed chunks.

### Step 6. Compute tremor files

For every generated IMU file, the pipeline computes a `.tr` file using `imu.wtremor()`.

If an IMU file is too short for the configured window size, tremor output may be skipped.

### Step 7. Persist `Tremor_file` metadata

The code saves a `Tremor_file` row per generated tremor file, again preserving:

- parent `record`
- parent `datafile`
- sensor
- initial timestamp
- final timestamp

### Step 8. Mark raw files processed

Once successful, each raw `Datafile` is marked `is_processed=True`.

### Step 9. Reset processing flag

The `finally` block clears `record.is_being_processed`, ensuring the record can be processed again if needed later.

---

## Bradykinesia Computation

Although the repository is mostly an ingestion/visualization platform, it already includes one concrete analytical metric: `compute_bradykinesia()`.

### What it does

It:

1. gathers accelerometer CSV files across the subject's continuous and ambulatory records,
2. filters each axis with a high-pass then low-pass filter,
3. computes periodograms,
4. finds the dominant frequency per axis,
5. keeps the axis with maximum power,
6. averages dominant frequencies across files,
7. maps the mean dominant frequency to a bradykinesia probability.

### Why this is architecturally important

This function demonstrates how the repository can evolve beyond raw-data management into clinically or behaviorally meaningful analytics.

For activity-recognition research, it suggests a natural future direction:

- replace or complement this heuristic with trained models,
- then store activity probabilities or episode detections in the same way.

---

## Dashboard Architecture

The dashboard is a classic server-rendered Django application with a JavaScript plotting layer.

## Access flow

1. User registers or logs in.
2. User verifies account by email.
3. User lands on the subject list.
4. User selects a subject.
5. User sees that subject's continuous and ambulatory records.
6. User opens a record page.
7. The page requests chart data from the same record URL via AJAX POST.

## Authentication flow

The dashboard uses Django auth plus a custom `Verification` model.

It supports:

- username/password login
- email-domain restrictions
- password complexity checks
- verification email sending
- login blocking until verification succeeds

This is helpful in collaborative research environments where access should be restricted to institutional users.

---

## Subject and Record Browsing Logic

## Subject listing

The index page does not list every subject in the database. It lists subjects that have at least one processed `Datafile`.

That is a subtle but meaningful design decision:

- it keeps the UI focused on subjects with usable data,
- and avoids presenting incomplete records as fully ready.

## Record listing

The subject detail page distinguishes:

- one continuous record, if present
- zero or more ambulatory records
- latest bradykinesia probability if available

That layout reflects the domain assumption that a subject may accumulate many task-based recordings over time but conceptually only one continuous stream record type.

---

## Data Export Logic

The record page supports direct download through:

```text
GET /record/<record_id>/?download=true
```

### Ambulatory export

For ambulatory records, the system zips the raw files and, when possible, appends the task ID to the exported filename so the archive is more self-descriptive.

### Continuous export

For continuous records, the zip includes:

- processed raw data files (`Datafile` CSVs),
- `tasks.csv` containing task IDs and time bounds,
- `positions.csv` containing position IDs and time bounds.

That export pattern is very helpful for offline feature engineering or model training because it preserves both the signals and the labels.

---

## Frontend Visualization Logic

This is the second most important technical area after the custom binary format.

The plotting system is implemented mainly in:

- `dashboard/static/dashboard/Plotter.js`
- `dashboard/static/dashboard/record.js`
- `dashboard/static/dashboard/constants.js`

It uses:

- D3.js for rendering and zooming
- Bootstrap for UI structure and styles
- server-rendered HTML templates for the page shell

## Visualization philosophy

The frontend is designed around an important constraint:

**long inertial recordings are too large to send to the browser in full every time the user zooms or switches sensor/metric.**

So the chart is not a static full-data plot. It is a request-driven viewport over the data.

That is a good architectural choice for sensor-heavy applications.

---

## Record page controls

The record page exposes three control groups:

### 1. Sensor selector

The user can switch between:

- accelerometer
- gyroscope

Only one sensor is active at a time.

### 2. Axis selector

The user can show/hide:

- x
- y
- z

These are multi-select in effect: any subset of axes can be shown.

### 3. Metric selector

The implemented metric options are:

- `tremor`
- `raw`

For ambulatory code paths there is also backend support for `spectrogram` and a placeholder for `energy`, although the current record page wiring is centered on the continuous-record viewer.

---

## How the chart is initialized

`record.js` instantiates a single `Plotter`.

The `Plotter` constructor:

1. locates the chart container,
2. reads the record type from a hidden DOM element,
3. creates an SVG,
4. attaches a D3 zoom behavior,
5. creates a translated chart group,
6. defines a clip path,
7. creates a line group inside the clipped area,
8. calls `resizeChart()`.

This produces a chart area where the plotted lines cannot overflow outside the intended viewport.

## Why the clip path matters

Without the clip path, panning and zooming long lines could draw outside the chart region. Using an SVG clip path is the correct low-level D3 solution for this kind of interactive plot.

---

## How data is requested from the server

When the plot loads or when a control changes, `Plotter.loadData()` issues a POST request to the current record URL.

The request body is JSON like:

```json
{
  "sensor": "accelerometer",
  "metric": "tremor",
  "samples": 1024,
  "timeRange": [1718628117678, 1718628217678]
}
```

Where:

- `sensor` is the selected sensor,
- `metric` is `raw` or `tremor`,
- `samples` is approximately the chart width in pixels,
- `timeRange` is either false/null for the full record or a selected zoom window.

The request includes the CSRF token from cookies.

This design is smart because it uses viewport width as a natural upper bound on returned sample count. There is no reason to send one million points to draw on a thousand-pixel chart.

---

## Server-side data preparation for visualization

The server-side logic lives mainly in `dashboard.utils.get_continuous_record_data()` and `dashboard.views.record()`.

### 1. Filter by sensor and time overlap

The backend first picks processed files (`Imufile` or `Tremor_file`) matching:

- the selected sensor
- and any overlap with the requested time range

### 2. Allocate sample budget proportionally per file chunk

If multiple processed files cover the requested range, the backend does not sample each equally. It assigns each file a number of samples proportional to its time coverage within the requested interval.

This is a very good detail because otherwise a short chunk could be overrepresented relative to a long chunk.

### 3. Read each file with decimation

The custom binary readers are called with `n_samples=file_n_samples`, which causes them to skip samples as needed.

### 4. Reconstruct timestamps

For each returned value row, the backend reconstructs timestamps using:

```text
file_initial_timestamp + step * header["delta_t"] * index
```

This is only possible because the `.imu` and `.tr` formats encode regularized time structure.

### 5. Return chunk boundaries

The response includes `limits`, a list of:

- `initial_timestamp`
- `final_timestamp`

for each processed chunk.

This is important because continuous recordings may have discontinuities. The frontend uses chunk boundaries to avoid drawing a single misleading line across gaps.

### 6. Return zoom scale hint

The backend also returns `step`, which the frontend uses as the upper zoom `scaleExtent`.

That is a clever way to couple sampling density and permissible zoom depth.

### 7. Apply smoothing before responding

For continuous-record POST responses, `dashboard.views.record()` applies a moving-average-like smoothing pass with `filter_size = 50`.

For each sample, it averages neighboring values within a local window and preserves the original timestamp.

Why this helps:

- it reduces visual noise in the plot,
- it makes high-level patterns easier to read,
- and it avoids burdening the browser with additional smoothing logic.

This is a presentation-oriented transformation, not a scientific replacement for the raw data. That distinction is important.

---

## Frontend normalization of tremor data

The tremor files return fields like:

- `x_frequency`
- `x_amplitude`
- `y_frequency`
- `y_amplitude`
- `z_frequency`
- `z_amplitude`

But the line renderer expects simple axis keys `x`, `y`, `z`.

So `Plotter.parseTremorToStandarFormat()` converts the payload into a standard plotting shape:

- one version for amplitudes,
- one parallel version for frequencies.

The plot currently uses the amplitude-normalized data for line rendering, while the frequencies are preserved in memory.

This separation is a good sign of a reusable plotting abstraction: different metric types can be adapted into a common x/y/z plotting interface.

---

## Automatic axis selection

When data is first loaded and no axis is selected yet, the frontend computes the mean value for each axis over the loaded data and auto-selects the axis with the largest mean.

This is a small but thoughtful UX feature. It ensures the chart is informative immediately, especially for tremor data where one axis may dominate.

Then the user can toggle any axis on or off manually.

Axis visibility is controlled by:

- adding/removing the `selected` CSS class on buttons,
- and drawing lines with or without the `opacity-0` class.

---

## How zoom works

The zoom behavior is one of the most interesting frontend mechanisms.

### Immediate visual response

As soon as the user zooms, D3 rescales the existing x-axis transform so the user sees responsive interaction.

### Debounced server refetch

After a short debounce (`150 ms`), the frontend:

1. reads the new visible time domain from the transformed x-scale,
2. stores it as `timeRange`,
3. sends a new POST request for just that temporal window,
4. rerenders the chart using the denser local data.

This hybrid strategy is excellent for large signals:

- immediate zoom feels smooth,
- but the final rendered data is still backed by a new server-sampled fetch rather than a stretched coarse dataset.

### Full-range cache plus local window merge

The `Plotter` stores:

- `allTimeData`: the broader full-range data
- `data`: the currently focused data

When zooming, the code merges the zoom-window data back with out-of-window cached data and then re-chunks it using the original `limits`.

That preserves the continuity model of the full record while still updating the current window detail.

### Chunk-preserving redraw

The merge-and-rechunk logic ensures that the frontend still draws separate paths for separate file/time chunks rather than fusing everything into a single continuous line.

This is exactly the right thing to do for sensor streams that may include recording gaps.

---

## Line rendering

Each selected axis is rendered separately.

For every data chunk:

- if the chunk has more than one point, draw a D3 path
- if it has exactly one point, draw a circle

This avoids the common edge case where tiny chunks disappear because a path with one point has no visible extent.

### Color coding

Axis colors are defined in `constants.js`:

- x: `#3B3486`
- y: `#7E2553`
- z: `#80BCBD`

The same axis color palette is reused across sensors.

### Axis units

Y-axis titles depend on both metric and sensor:

- raw accelerometer: `m/s^2`
- raw gyroscope: `deg/s`
- tremor views: `dB`

This is a good example of domain-specific display logic embedded in the frontend constants rather than scattered through rendering code.

---

## Ambulatory visualization path

The repository also contains code for ambulatory-record plotting:

- `dashboard/templates/dashboard/ambulatory-record.html`
- `dashboard/static/dashboard/ambulatory-record.js`
- backend helpers:
  - `get_ambulatory_record_trial_data()`
  - `get_ambulatory_record_trial_spectrogram()`

### Intended behavior

The intended ambulatory UI appears to be:

1. show task cards,
2. expand to list trials,
3. choose a trial,
4. fetch trial-specific data,
5. plot raw or derived metrics.

### What the backend supports

The backend can:

- load all rows for a task/trial pair,
- merge accelerometer and gyroscope rows,
- sort them by timestamp,
- and compute a spectrogram-like representation using ShortTimeFFT.

### Why this matters conceptually

This is exactly the sort of task-conditioned visualization needed in activity-prediction studies, because it allows researchers to compare repeated trials of known activities.

### Current state of the repo

The code for ambulatory plotting is present, but the record page template currently does not include the ambulatory task-selection partial, so the continuous-record viewer is the clearest fully integrated plotting path in the current codebase.

That does not reduce the importance of the ambulatory architecture; it simply means part of that flow looks mid-integration.

---

## Additional Utilities And Operational Components

## Logging

`utils.write_log()` writes daily log files under `log/` with:

- timestamp
- level
- message

This is used across modules for processing and mail failures.

## Email

`utils.send_mail()` uses local SMTP on `localhost`.

The dashboard uses this for verification email delivery. The separate `mailproxy/` endpoint provides a machine-callable wrapper around the same functionality.

## Manual data assessment helper

`assess-data.py` is a useful research utility. It scans a continuous record's CSV files and reports:

- gaps greater than 1000 ms
- unordered timestamps

This tells us the developers were actively concerned with signal integrity, not just storage.

That fits the overall philosophy of the repository.

---

## What This Project Enables In A Larger Activity-Recognition Stack

If you were building a full activity classification or daily-activity prediction platform, this repository would sit naturally in front of the model training and inference layers.

### It already solves the "dataset engineering" problem

Many activity-recognition efforts fail to scale because the team never builds a robust data model. Here, much of that foundational work is already done:

- subjects are normalized,
- sessions are modeled,
- files are typed by sensor,
- labels are queryable,
- timestamps are managed,
- and exports are available.

### It could feed classical ML pipelines

Examples:

- sliding-window statistical features from raw `.imu` data
- dominant-frequency features from `.tr` files
- task-conditioned feature extraction for supervised models
- continuous interval extraction for sequence models

### It could feed deep learning pipelines

Examples:

- fixed-size windows sampled from `Datafile_task_rel` intervals
- multimodal accelerometer + gyroscope fusion
- self-supervised pretraining on continuous streams
- weakly supervised models using task/position interval annotations

### It helps with labeling, not only storage

The presence of `Task`, `Position`, and temporal relation tables means this system is already thinking in terms of structured annotations, which is exactly what a serious modeling workflow needs.

---

## Current Implementation Notes And Caveats

This README describes the repository as it exists in code, but a few practical notes are worth keeping in mind.

### 1. The strongest implemented path is the continuous-record workflow

That includes:

- upload,
- overlap trimming,
- CSV sorting,
- IMU conversion,
- tremor derivation,
- on-demand plotting,
- and export.

Ambulatory support exists in models, backend helpers, and partial frontend code, but some of its template wiring appears incomplete.

### 2. Migrations are not committed

The repository contains `migrations/__init__.py` files, but no concrete migration history. So the schema is defined clearly in models, but reproducible database bootstrap would require generating migrations.

### 3. Environment configuration is only partially externalized

API keys are loaded from environment variables, but database credentials and Django secret material are hard-coded in `settings.py`. For a production or collaborative deployment, those should be moved to environment configuration.

### 4. This repo is mostly a platform layer, not the final predictive model

Its value is real and substantial, but it lives mainly in:

- data curation,
- preprocessing,
- storage design,
- derived feature generation,
- and exploratory visualization.

That is often the right architecture boundary for a research dashboard.

---

## Suggested Mental Model For The Whole System

The simplest way to understand this project is:

> NETremor Dashboard is a data-centric middleware layer between wearable/inertial acquisition and downstream behavioral analytics.

It does not merely collect files.

It:

- gives those files a subject and experimental context,
- regularizes them in time,
- stores them in efficient machine-friendly representations,
- attaches labels needed for learning,
- computes one derived movement metric,
- and exposes the results to researchers through a browser.

That makes it highly relevant to any project trying to infer or predict activities from daily-life inertial sensor data.

---

## Short Architectural Summary

If you only remember a few points, they should be these:

1. **The database design is one of the project's main strengths.** It cleanly separates subjects, records, files, tasks, positions, and derived metrics.
2. **The custom `.imu` and `.tr` formats are central.** They are what make fast, range-based visualization practical.
3. **The frontend is built around windowed server-side sampling, not full-data plotting.** That is the correct design for long sensor recordings.
4. **The project is already aligned with ML workflow needs.** It preserves labels, timestamps, sensor identity, and exportable structure.
5. **The codebase is best seen as an experimental data platform.** It is the layer that makes later activity-prediction models feasible and trustworthy.

---

## Main Files Worth Reading First

For a new developer or researcher, these files provide the clearest view of the system:

- `endpoint/models.py`: understand the domain schema
- `endpoint/views.py`: understand the upload contract
- `endpoint/utils.py`: understand ingestion and processing behavior
- `imu.py`: understand the custom formats
- `dashboard/utils.py`: understand how processed files are turned into plot-ready JSON
- `dashboard/views.py`: understand the download and visualization endpoints
- `dashboard/static/dashboard/Plotter.js`: understand the client-side rendering model

Those files together define most of the technical identity of the repository.
