# Chagan Lake Water Quality Monitoring

A local web application for retrieving, mapping, and reporting water-quality parameters for **Chagan Lake** from **Sentinel-3 OLCI** imagery.

The application combines ACOLITE atmospheric correction, geospatial processing, Random Forest regression models, GeoServer map publishing, and an interactive Flask web interface.

> This repository is currently a research/demo prototype designed for local deployment.

## Features

- Upload Sentinel-3 OLCI Level-1 data packages (`.zip`).
- Automatically unzip Sentinel data and locate the `.SEN3` product folder.
- Run ACOLITE atmospheric correction over the configured lake boundary.
- Convert corrected NetCDF reflectance bands to a resampled GeoTIFF.
- Clip the raster to the study-area boundary.
- Retrieve multiple water-quality parameters with Random Forest models:
  - Chlorophyll-a (Chl-a, `μg/L`)
  - Secchi disk depth / water transparency (SDD, `cm`)
  - Total phosphorus (TP, `mg/L`)
- Calculate summary statistics and produce GeoTIFF, PNG, and CSV outputs.
- Publish result layers to GeoServer and display them in an interactive Leaflet map.
- Generate a PDF report for completed analyses.

## Processing Workflow

```text
Sentinel-3 ZIP upload
  -> 7-Zip extraction
  -> ACOLITE atmospheric correction
  -> NetCDF reflectance bands to GeoTIFF
  -> Study-area clipping
  -> Random Forest retrieval
  -> GeoServer layer publishing
  -> Interactive map and PDF report
```

## Project Structure

```text
chagandemo/
├── app.py                 # Flask application entry point
├── routes.py              # Web routes and analysis workflow
├── core/                  # Pipeline controller and shared data objects
├── processors/            # Extraction, correction, conversion, clipping, and mapping steps
├── models/                # Trained Random Forest model files
├── data/
│   ├── shp/               # Chagan Lake boundary shapefiles
│   └── background/        # Optional background raster data
├── templates/             # Upload and interactive map pages
├── static/                # Web assets and generated reports/results
├── uploads/               # User-uploaded imagery (runtime data; do not commit)
├── temp/                  # Intermediate processing data (runtime data; do not commit)
├── tools/                 # Local third-party tools, such as ACOLITE and GeoServer
└── environment.yml        # Conda environment definition
```

## Prerequisites

- Windows (the current scripts and bundled tool paths target Windows).
- Python 3.10 or a compatible Conda environment.
- A running local GeoServer instance, normally available at `http://localhost:8080/geoserver`.
- ACOLITE and 7-Zip installed or configured under `tools/`.
- A Sentinel-3 OLCI Level-1 product packaged as a `.zip` file.

The project uses Python packages including Flask, GeoPandas, Rasterio, Xarray, Pyresample, Scikit-learn/Joblib, Matplotlib, Pandas, and GeoServer REST client libraries. Create the environment from the supplied definition:

```bash
conda env create -f environment.yml
conda activate <environment-name>
```

If the environment file does not include every dependency for your computer, install the missing package with Conda or pip and update `environment.yml` before sharing changes.

## Configuration

Before running the app, replace machine-specific paths and credentials with configuration values. In particular, inspect:

- paths to ACOLITE, GeoServer, model files, and output folders;
- the GeoServer URL, workspace, username, and password;
- the TianDiTu map API key used by the frontend;
- the lake-boundary shapefile paths.

For a shareable deployment, keep sensitive values in a `.env` file or environment variables rather than source code. Do not commit `.env` files, API keys, passwords, uploaded imagery, or generated outputs.

Example environment variables:

```ini
GEOSERVER_URL=http://localhost:8080/geoserver
GEOSERVER_USERNAME=admin
GEOSERVER_PASSWORD=change-me
TIANDITU_KEY=your-key-here
```

## Running Locally

1. Start GeoServer and make sure its REST and WMS services are reachable.
2. Confirm that ACOLITE, 7-Zip, shapefiles, and model files are available at the configured locations.
3. Activate the project environment.
4. Start the Flask application:

   ```bash
   python app.py
   ```

5. Open `http://127.0.0.1:5012` in a browser.
6. Upload a Sentinel-3 OLCI ZIP package, select one or more parameters, and start the analysis.

## Outputs

Each successful run can produce the following artifacts:

- A parameter-specific GeoTIFF raster for GeoServer publication.
- A PNG map preview.
- A CSV file containing valid retrieved pixel values.
- Summary statistics: minimum, maximum, mean, standard deviation, valid-pixel count, and 2nd/98th percentiles.
- An interactive WMS map layer served by GeoServer.
- A downloadable PDF analysis report.

## Notes and Limitations

- The current implementation is configured for **Chagan Lake** and **Sentinel-3 OLCI**.
- Retrieval models are only reliable within the conditions, locations, periods, and units represented by their training data. Validate them with in-situ observations before scientific or operational use.
- The processing pipeline is synchronous and may take considerable time for large source packages.
- Generated filenames and some outputs can be overwritten by later jobs; a task-based output layout is recommended before multi-user deployment.
- GeoServer publishing currently assumes a local workspace named `water_project`.

## Recommended Files to Exclude from Git

```gitignore
.env
.venv/
__pycache__/
*.pyc
.idea/

uploads/
temp/
static/reports/
static/results/

tools/geoserver/
tools/java/
tools/acolite_GUI/
tools/7zip/

*.zip
*.nc
*.tif
*.tiff
```

Decide separately whether to publish `models/*.pkl`. If the models are large, use Git LFS or provide a versioned download location and document how to obtain them.

## License

Add a license before publishing the repository. MIT is a simple choice for permissive reuse; GPL-3.0 is appropriate when derivative software must remain open source. Also verify the licenses of the bundled third-party tools, map services, model-training data, and satellite data before redistribution.
