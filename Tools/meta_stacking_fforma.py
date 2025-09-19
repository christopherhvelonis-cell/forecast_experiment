import pandas as pd
class FFORMAStacker:
    def __init__(self): self.fitted_=False; self.cols_=[]
    def fit(self, features: pd.DataFrame, losses: pd.DataFrame):
        self.cols_=list(losses.columns); self.weights_={c:1/len(self.cols_) for c in self.cols_}; self.fitted_=True; return self
    def predict_weights(self, new_features: pd.DataFrame) -> pd.DataFrame:
        assert self.fitted_; return pd.DataFrame({c:self.weights_[c] for c in self.cols_}, index=new_features.index)
