## data3001-data-f1-7

### Project Description

This project processes raw F1 telemetry data into an analytical dataset focused on optimizing vehicle dynamics at Melbourne's Albert Park Circuit. Strong cornering performance creates overtaking opportunities on the long straights and significantly impacts overall lap times. Specifically, we analyze how Temperature and pressure, position, throttle, brake and related controls, rotation and direction, speed and gravity, other dynamic data impact cornering speed and lap times.

#### Sources
2023 F1 Australian Grand Prix Telemetry in Melbourne Albert Park

### Workflow
Data cleaning: In order to ensure the product is stable and has no unusable rows, we removed some some parts of the data. Most importantly, Invalid laps, laps that were not on the Melbourne track, laps where driver status was invalid were all dropped. Some columns had missing values that were interpolated linearly or forward/backward filled. 

Crucially rows are grouped by 'M_SESSIONUID' then 'M_CURRENTLAPNUM' for indiscriminated lap to lap analysis, after relative independence and minimal correlation of the lap number was confirmed.

The data was sorted based on the variable `CURRENTLAPTIME` in order to make plotting simpler. Since the focus of the case study is the exit velocity coming out of Turn 1 and 2 into Turn 3, the data was limited to only include points that can be classified by the column `TURN` to be part of turn 1 or 2. 

Target engineering: Given the goal of this data project, we decided that the speed of the car when exiting the second turn was of paramount importance and is a good pick to be the target variable. The column, `exit_T2_speed` contains the target variable.

Feature engineering: In order to aid univariate and multivariate exploratory analysis, features that pertained to velocity, g-force, braking and throttling. 

Univariate Analysis: In order to gain insight into the most useful features in the data when predicting the target variable, univariate analysis will be conducted agains the target variable.

Multivariate Analysis: To find the most important features to be used in any modelling applications, the team has decided to conduct analysis between features, we will ensure that highly correlated variables are filtered and delt with accordingly.


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
Our team has completed data cleaning and started feature engineering on the raw F1 dataset. Key steps include filtering and validation, where we remove all races on different tracks and those with missing or unrealistic distance data, and restrict the dataset to only turns 1 and 2. Sorting, where we ordered the dataset into telemetry points chronologically. Feature engineering where we created the target variable which we decided is the exit speed of turn 2, as well as derived velocity and g-forces from positional and timestamp data. Lastly, data quality handling where we dropped all redundant, irrelevant or duplicate columns and applied interpolation to address missing datasets.

In the next step, univariate and multivariate analysis will be conducted for finding patterns, anomalies, and outliers, and adding new features where required. Each member will be given a specific domain. Rayaan on temperature/pressure, Tay on position, Yulun on dynamics, Gahan on throttle/braking, and Kevin on rotation, velocity, and g-forces. Results will then be combined to build a consolidated, modelling-ready dataset.

### Usage
Our data product is designed for performance modelling focusing on exit speed at turn 2, a critical performance metric which determines momentum onto the straight before turn 3. Although Linear Regression is an easily interpretable modelling technique to show how different features contribute to exit speed, our given data is heavily left-skewed, hence misaligned with our goal. This leads to predictions that are unrepresentative of what produces top performance. We propose Quantile regression as the usage for our data product to directly model the upper percentiles of exit speed. This approach captures conditions that will yield top exit speeds while still learning from the dataset. By shifting focus on the high-performance tail, quantile regression better suits race engineering objectives. Quantile regression allows for analysis of factors such as early throttle, steering stability and optimal braking point that help contribute to better outcomes.

In later stages of using our data product, more flexible methods should be explored including Random Forests (RF) or Ensemble Methods such as Adaptive boosting or Gradient Boosting. This is in order to capture nonlinearities and interactions while maintaining predictive power. RF will help identify complex dependencies concerning influence of throttle and lateral G-force on exit speed. Boosting methods should be used to improve accuracy concerning laps where exit speed deviates from expected values. 


#### Support Information
Main Contact: Kevin Zhou (Email: kevin7goestoheaven@gmail.com, z5342593@ad.unsw.edu.au)
#### Contributors
This data product is developed by our team as part of the Data Science Capstone Project. Rayaan, Tay, Yulun, Gahan and Kevin. Contributions are welcome via pull requests on GitHub. Please open an issue first to discuss proposed changes or feature requests.
