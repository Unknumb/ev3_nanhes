"""Custom loaders for SAS and mortality data files from URLs using pyreadstat."""

from typing import Any, Dict
from io import BytesIO
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
        
        # Read as space-delimited text file
        # The mortality file is typically space or tab delimited
        df = pd.read_csv(
            BytesIO(response.content),
            sep=r'\s+',  # Flexible whitespace delimiter
            engine='python'
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


