"""Custom loaders for SAS and mortality data files from URLs using pyreadstat."""

from typing import Any, Dict
from io import BytesIO, StringIO
import requests
import pyreadstat
import pandas as pd
from kedro.io import AbstractDataset


class SASDataset(AbstractDataset):
    """
    Custom Kedro dataset for loading SAS transport files (.xpt) from URLs.
    """
    
    def __init__(self, filepath: str, **kwargs):
        """
        Initialize the SAS dataset loader.
        
        Args:
            filepath: URL to the .xpt file
            **kwargs: Additional arguments
        """
        self.filepath = filepath
        self._data = None
    
    def _load(self) -> pd.DataFrame:
        """Load the SAS file from URL."""
        if self._data is not None:
            return self._data
            
        response = requests.get(self.filepath)
        response.raise_for_status()
        
        # Read the .xpt file from bytes
        df, meta = pyreadstat.read_xport(BytesIO(response.content))
        self._data = df
        
        return df
    
    def _save(self, data: pd.DataFrame) -> None:
        """Save is not supported for this dataset."""
        raise NotImplementedError("Saving SAS datasets is not supported")
    
    def _exists(self) -> bool:
        """Check if the remote file exists."""
        try:
            response = requests.head(self.filepath, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def _release(self) -> None:
        """Release cached data."""
        self._data = None
    
    @property
    def _version(self) -> None:
        """Return None as versioning is not supported."""
        return None


class MortalityDataset(AbstractDataset):
    """
    Custom Kedro dataset for loading NHANES Mortality linked data files from URLs.
    These are fixed-width format text files.
    """
    
    def __init__(self, filepath: str, **kwargs):
        """
        Initialize the Mortality dataset loader.
        
        Args:
            filepath: URL to the .dat file
            **kwargs: Additional arguments
        """
        self.filepath = filepath
        self._data = None
    
    def _load(self) -> pd.DataFrame:
        """Load the mortality data file from URL."""
        if self._data is not None:
            return self._data
            
        response = requests.get(self.filepath)
        response.raise_for_status()
        
        content = response.content.decode("latin-1", errors="ignore")

        # NHANES linked mortality files are fixed-width, not delimited.
        # FUTIME is read from the public follow-up months from MEC exam field.
        df = pd.read_fwf(
            StringIO(content),
            colspecs=[(0, 6), (14, 15), (15, 16), (45, 48)],
            names=["SEQN", "ELIGSTAT", "MORTSTAT", "FUTIME"],
            na_values=[".", "..", ""],
        )

        for column in ["SEQN", "ELIGSTAT", "MORTSTAT", "FUTIME"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        invalid_mortstat = sorted(
            df.loc[
                df["MORTSTAT"].notna() & ~df["MORTSTAT"].isin([0, 1]),
                "MORTSTAT",
            ].unique()
        )
        if invalid_mortstat:
            raise ValueError(
                "Invalid MORTSTAT values found after fixed-width parsing: "
                f"{invalid_mortstat}. Expected only 0, 1, or NaN."
            )

        self._data = df
        
        return df
    
    def _save(self, data: pd.DataFrame) -> None:
        """Save is not supported for this dataset."""
        raise NotImplementedError("Saving Mortality datasets is not supported")
    
    def _exists(self) -> bool:
        """Check if the remote file exists."""
        try:
            response = requests.head(self.filepath, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def _release(self) -> None:
        """Release cached data."""
        self._data = None
    
    @property
    def _version(self) -> None:
        """Return None as versioning is not supported."""
        return None

    def _describe(self) -> dict[str, Any]:
        """Describe the dataset configuration."""
        return {"filepath": self.filepath}


