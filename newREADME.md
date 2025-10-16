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
Loading data
First, we loaded the raw UNSW F1 2024 telemetry dataset using the read_data() function, then the related reference files, f1sim-ref-left.csv, f1sim-ref-right.csv, and f1sim-ref-line.csv, using the read_process_left(), read_process_right(), and read_process_line() functions. The Albert Park circuit's official track limits are represented by the left and right boundary files, which we used to confirm the accuracy of on-track data. These datasets were limited to the same coordinate range as the primary telemetry data to maintain spatial consistency. This alignment offers a solid geometric basis for the validation, racing-line analysis, and spatial filtering processes that follow.
Data cleaning
Upon initial exploration and plotting, we observed that the dataset contained laps from multiple circuits, not just the one of interest. To focus exclusively on the Albert Park track in Melbourne, we used the filter_melbourne() function to retain only laps recorded on that circuit. Further inspection revealed missing values in the world position coordinates and some duplicated rows, likely due to inconsistencies in the data collection process. Since the world X and Y coordinates (M_WORLDPOSITIONX_1 and M_WORLDPOSITIONY_1) form the foundation for all spatial analysis and visualisation, we removed any rows with missing values using the remove_na() function. This ensured that every telemetry point could be accurately positioned on the track, preventing issues with incomplete laps or plotting errors in later analysis. Additionally, several columns contained missing or duplicated information that did not contribute to modelling or analysis. These were removed using the remove_redundant_cols() function, leaving a clean and concise dataset suitable for further processing.
Lap Structuring
After cleaning the positional data, we structured the dataset to make it easier to analyse the laps. Using the re_index() function, we created a unique lap identifier, lap_index for each session–lap pair. This was done by grouping the data by session ID and current lap number, separating the dataset into distinct laps. This structure made it easier to visualise, compare, and summarise telemetry data on a per-lap basis, which is essential for subsequent analysis and modelling. 
To further ensure data quality and consistency, we applied the remove_stuttery_laps() function to eliminate laps with an insufficient number of distinct telemetry rows. This function identifies and removes laps containing fewer than 500 unique xy-coordinate points. Such laps typically result from duplicated or incomplete telemetry recordings, where the car’s position data appears static or discontinuous. By enforcing this threshold, only laps with a sufficiently dense and continuous stream of positional data were retained, ensuring that subsequent spatial analyses and performance modelling were based on complete and reliable lap data.
Spatial
Track Boundaries
The first step in this process involved using the define_cut_line() function, which automatically calculated the start and end coordinates of the sector’s boundary lines. Beginning from a reference point on the right side of the track, define_cut_line() determined the local direction of the boundary using neighbouring points and then constructed a perpendicular line extending across to the left boundary. The result was a line segment connecting the corresponding right and left boundary points, effectively defining the geometric “cut” across the circuit that marks the start and end of the selected track sector. By deriving these boundaries programmatically, we ensured consistency and reproducibility across all laps and sessions.
Once the entry and exit lines were defined, the track_slice() function was applied to the telemetry dataset. This function spatially restricted the data to the region enclosed between the start and end lines, effectively isolating the section of the track that covers Turns 1 and 2 of the Albert Park circuit. Through this process, we filtered out all other portions of the lap, allowing subsequent analyses and visualisations to focus exclusively on a consistent and well-defined track segment directly aligned with the main objective of our project.
Removing Invalid Tracks
Enforce_track_limits
During initial inspection, we noticed that several laps contained telemetry points located well outside the left and right track boundaries. According to racing regulations, a lap is considered valid only if at least one wheel of the car remains within the track limits at all times. Based on this guideline, we estimated the approximate width of a Formula 1 car and used it as a tolerance margin to determine whether a point was still within the legal track area. We then implemented the enforce_track_limits() function to validate each telemetry point against the geometric boundaries of the Albert Park circuit. Any laps containing points that exceeded these adjusted limits were removed, ensuring that the final dataset represented only valid, on-track driving behaviour suitable for further analysis and modelling.


Lap Summary and Feature Aggregation
Instead of analysing thousands of individual data points, we decided to condense each lap into a single row containing representative statistics such as average line deviation, braking and throttle behaviour, and proximity to key corners. This approach simplifies performance comparison between laps, drivers, or sessions and provides a modelling-ready dataset for regression or clustering analysis.
The initialise_lap_summary() function creates the foundational summary DataFrame, recording each lap’s index and total sector time. This is achieved by calculating the time difference between the first and last recorded timestamps (CURRENTLAPTIME) for each lap. This metric serves as a baseline measure of overall lap duration and enables subsequent analysis of how various features relate to performance time.
The avg_line_distance() function adds a measure of spatial consistency by computing the average deviation from the racing line for each lap. It groups all telemetry points by lap_index and averages their perpendicular distances to the reference line, giving an indicator of how closely a driver followed the optimal path through the circuit. Smaller average distances suggest better adherence to the ideal line and, generally, higher performance consistency.
The min_apex_distance() function calculates the minimum distance to each apex (Turns 1 and 2) for every lap. By using a KD-Tree nearest-neighbour search, it determines how close a driver’s trajectory came to the ideal apex points. This helps quantify cornering precision — laps that approach the apex more closely are typically associated with smoother and faster cornering performance.
The add_avg_brake_pressure() and add_avg_throttle_pressure() functions compute the mean brake and throttle pressures across each lap. These values summarize a driver’s overall input style — for example, whether a lap involved aggressive braking or smooth, consistent throttle application. Such aggregates are useful for distinguishing different driving strategies and their influence on lap time.
The add_peak_brake_pressure() and add_peak_throttle_pressure() functions record the maximum brake and throttle inputs within each lap. These features capture extremes of driver control and can reveal how much braking force or acceleration was applied in key segments. Comparing these peak values across laps helps assess consistency in control inputs and vehicle dynamics under varying cornering conditions.
The first_braking_point() function identifies the first instance of braking within each lap where the brake input exceeds a set threshold (default = 0.2). It records the spatial coordinates (brake_x, brake_y) and pressure at that point. This allows analysts to determine how early or late drivers initiate braking before entering Turn 1, which is crucial for studying braking strategy and corner entry efficiency.
Similarly, the first_turning_point() function detects the first steering action beyond a set threshold (default = 0.2 in either direction). It logs the corresponding coordinates and steering angle, representing the moment a driver begins turning into the corner. Comparing the timing and position of these first turning points across laps reveals differences in driver anticipation and line approach into the corner sequence.
Finally, the summary_eng() function orchestrates all the above computations to produce the completed lap summary dataset. It integrates each lap’s timing, geometric, and control-input features into a single, comprehensive table. This summary provides an interpretable, lap-level view of performance — simplifying analysis, enabling efficient visualisation, and supporting downstream modelling tasks such as predicting lap times or evaluating driver behaviour.


Telemetry Feature Engineering
We decided to engineer some features that will provide point-level telemetry into interpretable, modelling-ready features that describe how the car is driven through Turns 1–2. Instead of only relying on lap aggregates, we compute per-sample signals that capture driver behaviour, vehicle dynamics, and line efficiency. These features power visual analyses and serve as inputs for downstream models that relate control inputs and trajectory to outcomes like corner-exit speed or sector time.

telemetry_eng(df)
This orchestration function runs the end-to-end telemetry feature pass. It (i) marks Turn-1/Turn-2 windows around the apexes, (ii) repairs steering gaps via interpolation, (iii) loads the reference racing line and computes each sample’s distance to it, (iv) builds a composite brake–throttle signal, (v) recomputes physically consistent velocity and G-force from positions and timestamps, (vi) derives three alignment angles (front-wheel vs velocity, car direction vs velocity, and front-wheel vs car direction) to quantify under/oversteer and steering aggression, and (vii) computes brake temperature balance. The result is a single DataFrame with rich, physics-aware features that explain how a lap was driven, not just how fast it was.
interpolate_wheel_angle(df)
Fills small gaps in M_FRONTWHEELSANGLE within each lap using linear interpolation (plus forward/back fill). Steering is a key control input; missing values can distort angle-based features and visualisations. Interpolation produces a continuous steering signal, enabling stable angle metrics and fair comparisons across laps.
compute_turning_window(df)
Tags whether each sample is within a turning window around the T1 and T2 apexes using a distance threshold (e.g., 50 m). It also stores continuous distances to both apexes. These flags and distances focus analysis on the high-impact parts of the complex (entries, apexes, exits), enabling targeted summaries and models that compare behaviour inside versus outside the corners.
racing_line_deviation(df, line)
Computes each sample’s perpendicular distance to a reference racing line using a KD-Tree nearest-neighbour lookup. This yields line_distance, a compact measure of line adherence. Smaller distances generally indicate more efficient pathing and correlate with smoother speed retention and better exit velocities.
brake_throttle(df)
Creates a composite driver-input signal, M_BRAKE_THROTTLE_1 = M_THROTTLE_1 − M_BRAKE_1. This encodes the decelerate→coast→accelerate sequence on a single axis, simplifying visualisation and modelling of control strategy through the S-curve. Higher values indicate net throttle; lower values indicate net braking.
recompute_velocity_and_gforce(df)
Recomputes velocity (VEL_X/Y/Z) from position deltas and timestamps, then differentiates velocity to obtain G-forces (GFORCE_X/Y/Z), with clipping of unrealistic outliers and per-lap interpolation. Doing this from first principles ensures internal consistency when upstream filters or resampling have affected the original telemetry, yielding physically plausible signals for dynamics analysis.
front_wheel_vs_velocity(df)
Computes the angle between the front-wheel direction (car forward vector rotated by steering angle) and the velocity vector. Large deviations indicate potential understeer or tyre slip (the wheels point somewhere different to where the car is actually moving). This feature helps relate steering inputs to realised motion.
car_direction_vs_velocity(df)
Computes the angle between the car’s facing direction and its velocity vector. Elevated values indicate drift/slide/oversteer, where the chassis orientation and travel direction diverge. This is useful for diagnosing stability and traction through the change of direction between T1 and T2.
front_wheel_vs_car_direction(df)
Computes the angle between the front-wheel direction and the car’s facing direction to quantify steering aggression and responsiveness (how far the wheels are turned relative to the chassis). Peaks often align with turn-in or recovery phases and can indicate sharp corrections or sustained steering loads.
compute_brake_balance(df)
Derives front–rear and left–right brake temperature balance: brake_front_rear_diff (front avg − rear avg) and brake_left_right_diff (left avg − right avg). These proxies reflect brake bias and potential lateral imbalance (e.g., repeated right-handers heating left brakes more). They help connect mechanical state to handling (tendency to under/oversteer) and to driver braking style.

### Data Description

Data Description
After the complete cleaning and spatial filtering process, the final dataset consists of approximately 774,772 rows and 59 columns, representing valid telemetry data points recorded during the first two turns (Turns 1–2) of the Albert Park Circuit. Each row corresponds to a single telemetry sample captured within these turns, while each column represents a signal, sensor reading, or engineered feature. The dataset has been geometrically validated using track boundaries, start and end cut lines, and strict on-track constraints to ensure that only realistic racing behaviour is retained.
The final data product is designed for high-quality, reproducible modelling and visualisation. All laps were spatially aligned using the define_cut_line() and track_slice() functions to ensure a consistent reference frame across sessions. Following filtering, additional feature engineering was performed in a layered, progressive approach divided into Basic Features and Advanced Features, each building on the previous layer to quantify driver performance, vehicle behaviour, and cornering efficiency.
Engineered and Derived Features 
Group
Column(s)
Description 
Lap Counter 
lap_index
Derived from ordered laps; used for grouping and plotting
Distance to corner apex (m)
dist_to_t1_apex, dist_to_t2_apex
Calculated from car position and track geometry
Boolean indicators
is_t1_window, is_t2_window
True if sample lies within each corner’s analysis window
Along-path distance (m)
Line_distance


Computed after geometric alignment with track_slice()
Combined control metric
M_BRAKE_THROTTLE_1
Derived to measure brake-throttle overlap
Velocity components (m/s)
VEL_X, VEL_Y, VEL_Z
Decomposed from world velocity vectors
Lateral, longitudinal, and vertical G-forces (g)
GFORCE_X, GFORCE_Y, GFORCE_Z
Calculated from motion and orientation vectors
Angular differences (radians)
angle_fw_vs_vel, angle_car_vs_vel, angle_fw_vs_car
Quantify slip and directional misalignment
Temperature differentials (°C)
brake_front_rear_dif, brake_left_right_diff
Derived from brake temperatures; indicate load imbalance

Original Telemetry Variables 
Group
Column(s)
Description
Identifiers & Metadata
M_SESSIONUID, lap_index, M_CURRENTLAPNUM
Unique session and lap identifiers used to distinguish individual laps and group telemetry data.
Timing Information
M_TIMESTAMP, M_CURRENTLAPTIMEINMS_1, M_LASTLAPTIMEINMS_1, M_LAPTIMEINMS, M_TOTALDISTANCE_1, LAPTIME, CURRENTLAPTIME, SECTOR1TIME, SECTOR2TIME, SECTOR3TIME, M_SECTOR1TIMEINMS, M_SECTOR2TIMEINMS, M_SECTOR3TIMEINMS, RACETIME
Timing-related variables including total race time, sector splits, and lap timing in both milliseconds and seconds. Used to measure performance consistency and compute sector times.
Position & Geometry
M_WORLDPOSITIONX_1, M_WORLDPOSITIONY_1, M_WORLDPOSITIONZ_1, M_TRACKLENGTH, TURN
Car’s spatial coordinates in 3D world space (X, Y, Z), track length, and current turn number. Used for visualising trajectories and slicing the dataset by track segments.
Velocity & Direction
M_WORLDVELOCITYX_1, M_WORLDVELOCITYY_1, M_WORLDVELOCITYZ_1, M_WORLDFORWARDDIRX_1, M_WORLDFORWARDDIRY_1, M_WORLDFORWARDDIRZ_1, M_WORLDRIGHTDIRX_1, M_WORLDRIGHTDIRY_1, M_WORLDRIGHTDIRZ_1, M_SPEED_1
Instantaneous car velocity components (m/s) and orientation vectors describing the car’s heading and lateral direction. Used to calculate motion dynamics and trajectory curvature.
Driver Inputs & Controls
M_THROTTLE_1, M_BRAKE_1, M_STEER_1, M_GEAR_1, M_FRONTWHEELSANGLE, M_DRS_1
Real-time driver control inputs such as throttle percentage, brake pressure, steering input, gear selection, and DRS activation. Core signals for understanding driver behaviour.
Vehicle State & Dynamics
M_ENGINERPM_1, M_BRAKESTEMPERATURE_RL_1, M_BRAKESTEMPERATURE_RR_1, M_BRAKESTEMPERATURE_FL_1, M_BRAKESTEMPERATURE_FR_1, M_TYRESPRESSURE_RL_1, M_TYRESPRESSURE_RR_1, M_TYRESPRESSURE_FL_1, M_TYRESPRESSURE_FR_1, M_GFORCELATERAL_1, M_GFORCELONGITUDINAL_1, M_GFORCEVERTICAL_1, M_YAW_1, M_PITCH_1, M_ROLL_1
Telemetry describing the mechanical and physical state of the car, including engine RPM, brake and tyre temperatures/pressures, G-forces, and body orientation. Used for performance and safety analysis.
Derived Spatial Features
dist_to_t1_apex, dist_to_t2_apex, is_t1_window, is_t2_window
Engineered metrics showing distance from the car to each turn’s apex, and binary indicators for whether the car is within the Turn 1 or Turn 2 analysis window. These are key for targeted corner analysis.
Performance & Sector Metrics
M_LAPDISTANCE_1, M_TOTALDISTANCE_1, M_LAPTIMEINMS, M_TRACKLENGTH, lap_index
Distance and lap metrics used to compute per-lap performance, lap segmentation, and consistency checks.
Additional Reference Columns
R_NAME
Reference or label for the race/session (e.g., track name or event ID). Used for contextual grouping or validation.



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
