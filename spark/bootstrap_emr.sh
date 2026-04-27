#!/bin/bash
set -e
echo "Starting EMR bootstrap action"
pip3 install --upgrade pip
pip3 install pyspark==3.5.0 pandas==2.2.0 matplotlib==3.8.0 seaborn==0.13.0 transformers==4.38.0 datasets==2.18.0 pyarrow==15.0.0
echo "Bootstrap action complete"