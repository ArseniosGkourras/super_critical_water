import os
import subprocess

def submit_jobs_in_current_directory():
    """
    Runs 'sbatch submit.sh' in each subdirectory of the current working directory if 'submit.sh' exists.
    """
    # Get the current working directory
    parent_dir = os.getcwd()
    
    # Iterate over each item in the current directory
    for dir_name in os.listdir(parent_dir):
        # Full path of the subdirectory
        dir_path = os.path.join(parent_dir, dir_name)
        
        # Check if it is a directory and contains 'submit.sh'
        submit_file = os.path.join(dir_path, "submit.sh")
        if os.path.isdir(dir_path) and os.path.isfile(submit_file):
            try:
                # Run 'sbatch submit.sh' in the directory
                print(f"Submitting job in directory: {dir_path}")
                subprocess.run(["sbatch", "submit.sh"], cwd=dir_path, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to submit job in {dir_path}: {e}")
            except Exception as e:
                print(f"Unexpected error in {dir_path}: {e}")

# Run the function to submit jobs in the current working directory
submit_jobs_in_current_directory()
