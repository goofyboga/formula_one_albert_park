## data3001-data-f1-7

## Project Description

This project transforms raw Formula 1 telemetry data into a refined dataset aimed at understanding and improving cornering performance at Melbourne’s Albert Park circuit. Our goal is to uncover how environmental, mechanical, positional, and control variables influence cornering speed and ultimately lap times.

In F1 racing, cornering is a critical performance lever: how fast a car carries speed through turns influences its exit velocity onto the straights, which in turn affects overtaking potential and total lap time. Small gains in cornering stability or speed can cascade into large gains over a race. By identifying the data-driven relationships between inputs (throttle, brake, steering) and outputs (speed, lap time), this work could help refine setups or driver decisions under varying conditions. Moreover, doing this analysis specifically for Albert Park adds contextual relevance, as track geometry and elevation changes all factor in uniquely.

Prior studies in motorsports analytics often lean on simplified simulations, idealized models, or coarse-grained datasets. Some works examine driver behavior broadly or compare whole-lap times, but few dissect corner-level dynamics in detail, especially combining raw telemetry and environmental data. Our approach builds on that literature by working with high-resolution frame-level telemetry and focusing on a specific circuit to localize the insights.

We will ingest telemetry streams that include vehicle position, velocity, orientation, rotational data, and driver control signals (throttle, brake). These will be merged with session metadata (e.g. timestamping) and environmental readings (track temperature, ambient pressure). We’ll preprocess the data to clean, sync, and align frames, filter for the relevant track sections (corners), and engineer derived features (e.g. angular acceleration, lateral G forces, steering input gradients). From there, modeling (e.g. regression, decision trees) will seek to quantify and predict performance under varying scenarios.


## Sources
2024 F1 Australian Grand Prix Telemetry in Melbourne Albert Park：
The primary data source for this project is the 2024 Formula 1 Australian Grand Prix telemetry dataset, recorded at the Melbourne Albert Park Circuit. This telemetry data provides high-frequency measurements capturing the behavior of F1 cars as they navigate the circuit. The dataset includes several categories of information that together create a comprehensive picture of vehicle performance and driver interaction.

### Vehicle positioning and motion data:
The first key source component is vehicle positioning and motion data, which records the car’s 3D spatial coordinates (M_WORLDPOSITIONX_1, M_WORLDPOSITIONY_1, M_WORLDPOSITIONZ_1), velocity components (M_WORLDVELOCITYX_1, M_WORLDVELOCITYY_1, M_WORLDVELOCITYZ_1), and orientation vectors (M_WORLDFORWARDDIRX_1, M_WORLDRIGHTDIRY_1, etc.). These readings describe how the car moves and rotates along the circuit, allowing for reconstruction of trajectories and calculation of cornering forces.

### Driver control inputs:
The second key source is driver control input data, which captures real-time human actions such as throttle percentage (M_THROTTLE_1), braking intensity (M_BRAKE_1), steering angle (M_STEER_1), and gear selection (M_GEAR_1). These variables are crucial for understanding how driver decisions influence the car’s dynamic response and how control inputs correlate with speed, stability, and efficiency through corners

### Session metadata and timing information:
Finally, session metadata and timing information—including variables like M_TIMESTAMP, M_CURRENTLAPTIMEINMS_1, M_SECTOR1TIMEINMS, and RACETIME provide temporal and contextual structure to the telemetry. This ensures accurate alignment across laps, sectors, and sessions, while enabling detailed performance comparisons.

Together, these three components create a comprehensive, multi-dimensional dataset of approximately 774,000 telemetry samples and 59 variables, validated through geometric alignment and filtering to retain only realistic, on-track racing data. This dataset serves as a robust foundation for modeling vehicle dynamics, evaluating driver behavior, and optimizing cornering performance at Albert Park.

### Data Creation
In order to create and access the data product. You must run create_data.py in the root of this repository. This script expects the following file structure. 

    data3001-data-f1-7/
        ├── create_data.py
        └── data/
            ├── f1sim-ref-left.csv
            ├── f1sim-ref-right.csv
            ├── f1sim-ref-line.csv
            └── UNSW F12024.csv


The script will produce telemetry.csv, summary.csv, left.csv, right.csv, line.csv. the most important products are telemetry.csv, which is the point-by-point lap data, and summary.csv, which is the high-level overview of each lap. 


### Workflow
Data cleaning: In order to ensure the product is stable and has no unusable rows, we removed some some parts of the data. Most importantly, Invalid laps, laps that were not on the Melbourne track, laps where driver went too far off trac or there was not enough data were also dropped.  

Crucially rows are grouped by `lap_index` for indiscriminated lap to lap analysis, after relative independence and minimal correlation of the lap number was confirmed. 

The start and finish lines were calculated in order to find efficient cuttoffs for the parts of the laps we wished to analyse. This made target engineering straightforward. Given the goal of this data project, we decided that the time taken to complete this section of the track would be an apt target variable. 

Feature engineering: In order to aid univariate and multivariate exploratory analysis, features that pertained to velocity, g-force, braking and throttling were interpolated. While other stats were created from scratch. Features regarding the lap span two data sets. telemetry.csv, which provide point-by-point detailed insight into each lap, while summary.csv provides high level insight into the laps, highlighting key moments. 


### Data Description

After cleaning, there are approximately 35,527 rows x 56 columns. Basic features have been engineered to quantify driver behavior, vehicle dynamics, and turn efficiency. We are doing a layered progressive approach divided into Basic Features and Advanced Features.

Basic Features

- Speed-based metrics: For each turn window (entry to exit), we extract `entry_speed`, `apex_speed`, `exit_speed`, `mean_speed`, `max_speed`, `speed_drop` (entry minus apex), and `speed_gain` (exit minus apex). These capture how the driver modulates speed through the turn and identify recovery efficiency.
- Velocity and G-force aggregates: Maximum, mean, and standard deviation of `VEL_X/Y/Z` and `GFORCE_X/Y/Z`, lateral and longitudinal peaks, and apex/exit G-values capture vehicle dynamics and driver load management.
  
Advanced Features

- Brake/Throttle features: A combined variable, `M_BRAKE_THROTTLE_1` = `M_THROTTLE_1` - `M_BRAKE_1`, allows visualizing and quantifying driver control strategy. Additional features track the first brake point, brake distance to apex, brake duration, and throttle resumption metrics. This enables analysis of how drivers balance deceleration and acceleration for optimal corner exit.

- Steering and orientation metrics: Maximum and mean steering angle, steering rate, yaw/pitch/roll ranges, and optional steering at apex. These features provide insight into control precision, corrective maneuvers, limiting understeering/oversteering.

- Trajectory and directional metrics: Average forward and lateral vectors, heading change, and estimated turn radius quantify the path efficiency through the turn.

Two features are showcased below to the marker to demonstrate our comprehensive approach:

- Exit speed at Turn 2 (`exit_T2_speed`) – Serves as the primary target variable. Outliers below 175 km/hr were removed to focus on meaningful performance data, and a log transformation was applied to reduce skew and heteroscedasticity. Visualizing the top-performing range (240–250 km/hr) reveals that the fastest lines consistently hug the track boundaries, confirming the S-shaped apex-hugging pattern.

- Brake-throttle combination (`M_BRAKE_THROTTLE_1`) – an advanced feature showcasing driver control strategy. By plotting the highest exit speeds against this variable, it becomes clear that smoother, earlier braking followed by gradual throttle yields more efficient corner exits.

These visualizations reflect deliberate design choices, balancing performance relevance, interpretability, and analytical insight. Feel free to click on the images below for proper detail and zoom!

<table>
  <tr>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/216c0449-cf1d-4b91-b64b-2ff858e9a943" width="480"/><br/>
      <sub><b>Optimized Exit Speed Line T2</b></sub>
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/a3ba7261-adf9-4d9b-befb-bdfb48d30ed9" width="480"/><br/>
      <sub><b>Brake–Throttle Balance on Peak Exit Speeds</b></sub>
    </td>
  </tr>
</table>

**Our Hypothesis: Apex-Hugging and Curvature Optimization**

We hypothesize that optimal cornering through the S-shaped Turns 1–2 is achieved by hugging track boundaries and minimizing transition time between apexes. By maximizing the local turning radius $R=\frac{1}{k}$ where $k$ is curvature, drivers reduce lateral acceleration peaks and maintain momentum. Properly aligning the car’s momentum with steering and wheel orientation further limits understeer or oversteer. Smoother transitions between apexes minimize speed loss, leading to higher exit speeds. Visualizing exit speed along this trajectory, overlaid with the brake-throttle control variable, allows us to assess how effectively drivers balance braking and throttle inputs and whether the fastest trajectories follow the ideal racing line.

### Project Status
Our team has completed data cleaning and started feature engineering on the raw F1 dataset. Key steps include filtering and validation, where we remove all races on different tracks and those with missing or unrealistic distance data, and restrict the dataset to only turns 1 and 2. Sorting, where we ordered the dataset into telemetry points chronologically. Feature engineering where we created the target variable which we decided is the exit speed of turn 2, as well as derived velocity and g-forces from positional and timestamp data. Lastly, data quality handling where we dropped all redundant, irrelevant, duplicate or columns with zero variance (no predictive power). We applied interpolation and filling methods to address missing data that were consequential such as XYZ velocity, G-force and wheel angles. 

In the next step, univariate and multivariate analysis will be conducted for finding patterns, anomalies, and outliers, and adding new features where required. Each member will be given a specific domain. Rayaan on temperature/pressure, Tay on position, Yulun on dynamics, Gahan on throttle/braking, and Kevin on rotation, velocity, and g-forces. Results will then be combined to build a consolidated, modelling-ready dataset.

### Usage
Our data product is designed for performance modelling focusing on exit speed at turn 2, a critical performance metric which determines momentum onto the straight before turn 3. Although Linear Regression is an easily interpretable modelling technique to show how different features contribute to exit speed, our given data is heavily left-skewed, hence misaligned with our goal. This leads to predictions that are unrepresentative of what produces top performance. We propose Quantile regression as the usage for our data product to directly model the upper percentiles of exit speed. This approach captures conditions that will yield top exit speeds while still learning from the dataset. By shifting focus on the high-performance tail, quantile regression better suits race engineering objectives. Quantile regression allows for analysis of factors such as early throttle, steering stability and optimal braking point that help contribute to better outcomes.

In later stages of using our data product, more flexible methods should be explored including Random Forests (RF) or Ensemble Methods such as Adaptive boosting or Gradient Boosting. This is in order to capture nonlinearities and interactions while maintaining predictive power. RF will help identify complex dependencies concerning influence of throttle and lateral G-force on exit speed. Boosting methods should be used to improve accuracy concerning laps where exit speed deviates from expected values. 


#### Support Information
Main Contact: Kevin Zhou (Email: kevin7goestoheaven@gmail.com, z5342593@ad.unsw.edu.au)
#### Contributors
This data product is developed by our team as part of the Data Science Capstone Project. Rayaan, Tay, Yulun, Gahan and Kevin. Contributions are welcome via pull requests on GitHub. Please open an issue first to discuss proposed changes or feature requests.
