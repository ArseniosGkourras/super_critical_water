#!/bin/bash
#SBATCH --job-name=lammps_2020_job          # Job name
#SBATCH --output=lammps_output_%j.log       # Output file (%j will be replaced with the job ID)
#SBATCH --error=lammps_error_%j.log         # Error file (%j will be replaced with the job ID)
#SBATCH --time=70:00:00                     # Maximum job run time
#SBATCH --partition=prod-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=8                          # Number of MPI tasks
#SBATCH --cpus-per-task=1                   # CPUs per MPI task
#SBATCH --mem=54G                           # Memory allocation
#SBATCH --mail-type=END,FAIL                # Notifications on job end or failure
#SBATCH --mail-user=your_email@example.com  # Replace with your email

set -e   # Exit on error
set -u   # Treat unset variables as errors
set -x   # Print executed commands

module load mpi/openmpi-x86_64
# Uncomment if you need Apptainer module
# module load apptainer

# Set OpenMP threads to 1
export OMP_NUM_THREADS=1

# Get the original directory name
ORIGINAL_DIR_NAME=$(basename "$(pwd)")

# Define a unique scratch directory for each job
SCRATCH_DIR="/tmp/${ORIGINAL_DIR_NAME}_${SLURM_JOB_ID}"
mkdir -p "$SCRATCH_DIR"

# Save the original directory name in a file
echo "$ORIGINAL_DIR_NAME" > "$SCRATCH_DIR/original_dir_name.txt"

# Copy only the current directory's contents (not parent directories)
cp -r . "$SCRATCH_DIR/"

# Navigate to the scratch directory
cd "$SCRATCH_DIR"

# Run LAMMPS using Apptainer
apptainer exec /project/containers/lammps_2023_aug.sif mpirun -n $SLURM_NTASKS lmp -in run.lmp

# Copy results back without overwriting previous results
RESULT_DIR="$SLURM_SUBMIT_DIR/results_${SLURM_JOB_ID}"
mkdir -p "$RESULT_DIR"
cp -r "$SCRATCH_DIR"/* "$RESULT_DIR"

# Commented out cleanup to keep files in /tmp/
rm -rf "$SCRATCH_DIR"
