#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set environment variables to prevent OpenMP conflicts
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# Run the application with proper multiprocessing cleanup
python run_app.py
