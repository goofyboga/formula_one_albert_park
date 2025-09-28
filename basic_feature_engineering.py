import pandas as pd 
import numpy as np

def optimize_target_variable(df):
    """
    Optimizing the target variable by cutting off outliers, before using a log
    transformation to treat heteroscadasticity and imbalance. Highly recommend
    during modelling to use quantile regression strategies to deal with the heavy
    left skew of the target variable. 

    Example Usage: f1_cleaned_df = optimize_target_variable(f1_cleaned_df)
    """
    df = df[df["exit_T2_speed"] >= 175] # Clear outliers (invalid or non consequential speed)
    df["exit_T2_speed_log"] = np.log(df["exit_T2_speed"]) # Reduce target variable imbalance
    return df
