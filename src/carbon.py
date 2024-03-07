from numpy import array
import numpy as np
import pandas as pd
from pandas.core.frame import DataFrame


class CarbonModel():
    def __init__(self, name, df: DataFrame, carbon_start_index, carbon_error) -> None:
        self.name = name
        self.df = df
        self.carbon_start_index = carbon_start_index
        self.carbon_error = carbon_error
        self.mean = self.df["carbon_intensity_avg"].mean()
        self.std = self.df["carbon_intensity_avg"].std()

    def reindex(self, index):
        df = self.df[index:].copy().reset_index()
        model = CarbonModel(self.name, df, self.carbon_start_index, self.carbon_error)
        return model

    def subtrace(self, start_index, end_index):
        df = self.df[start_index:start_index + end_index].copy().reset_index()
        model = CarbonModel(self.name, df,self.carbon_start_index, self.carbon_error)
        return model
    
    def extend(self, factor):
        df = pd.DataFrame(np.repeat(self.df.values, factor, axis=0), columns=["carbon_intensity_avg"])
        df["carbon_intensity_avg"] /= factor
        model = CarbonModel(self.name, df,self.carbon_start_index, self.carbon_error)
        return model
        

    def __getitem__(self, index):
        return self.df.iloc[index]['carbon_intensity_avg']


def get_carbon_model(carbon_trace:str, carbon_start_index:int, carbon_error="ORACLE") -> CarbonModel:
    df = pd.read_csv(f"src/traces/{carbon_trace}.csv")
    df = df[17544+carbon_start_index:17544+carbon_start_index+720]
    #df = pd.concat([df.copy(), df[:1000].copy()]).reset_index()
    df = df[["carbon_intensity_avg"]]
    df["carbon_intensity_avg"] /= 1000
    c = CarbonModel(carbon_trace, df, carbon_start_index, carbon_error)
    return c
