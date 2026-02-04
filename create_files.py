import os
import shutil

def create_directories_with_files(temp_range, pressure_range=None,
                                  constant_temp=None, constant_pressure=None,
                                  base_dir="simulations"):
    """
    Creates directories for each (temperature, pressure) pair under base_dir
    and populates them with run.lmp and required auxiliary files.
    """
    if constant_temp is not None:
        temp_range = [constant_temp]
    if constant_pressure is not None:
        pressure_range = [constant_pressure]

    if pressure_range is None:
        pressure_range = [1.01325]  # bar, ~1 atm

    # Ensure base output directory exists
    os.makedirs(base_dir, exist_ok=True)

    # Convert bar → atm (LAMMPS "real" units typically expect atm)
    pressure_range_atm = [p * 0.986923 for p in pressure_range]

    files_to_copy = [
        "system.in.init",
        "system.in.settings",
        "system.data",
        "diffusivity_msd.in.prop",
        "viscosity.in.prop",
        "submit.sh",
    ]

    for temp in temp_range:
        for pressure_bar, pressure_atm in zip(pressure_range, pressure_range_atm):
            folder_name = f"T_{temp}_P_{pressure_bar}"
            dir_path = os.path.join(base_dir, folder_name)
            os.makedirs(dir_path, exist_ok=True)

            lammps_script_content = f"""
variable        temp equal {temp}
variable        press equal {pressure_atm}
#neighbor 0.5 bin 
boundary        p p p

include "system.in.init"
read_data "system.data"
include "system.in.settings"

variable TEql equal ${{temp}} # K

#----- conversion factors and coefficients

variable ps2fs equal 1e3
variable ns2fs equal 1e6
variable ms2fs equal 1e9
variable fs2s equal 1e-15
variable atm2Pa equal 101325.0
variable A2m equal 1.0e-10

variable kB equal 1.3806504e-23 # [J/K] Boltzmann


# MD setting
group           water type 7 8
neighbor        2.0 bin
neigh_modify    every 1 delay 10 check yes

write_data initial_config.data

velocity        all create ${{temp}} 54654
variable dt equal 1
timestep        1

# rigid MD 
thermo_style    custom step time temp press pe ke etotal enthalpy atoms lx ly lz vol density
thermo 1000

velocity   water create ${{temp}} 3125  loop local  dist gaussian
fix md_nvt water nvt temp ${{temp}} ${{temp}} $(100.0*dt)

run         1000000

# SECTION:  ADD to FIX and UNFIX to enable  NVT-PRODUCTION !
unfix       md_nvt 

# RUN-NPT
fix md_npt water npt temp ${{temp}} ${{temp}} $(100.0*dt) iso ${{press}} ${{press}} $(1000.0*dt)

#-------------------------- Dump the time-averaged global properties --------------------------

variable s equal 10    # sample interval
variable p equal 100   # correlation length
variable d equal $s*$p # dump interval to calculate thermodynamic properties

# get thermodynamic properties 
variable time equal time
variable Vout equal vol
variable Pout equal press
variable Tout equal temp
variable Hout equal enthalpy
variable PEout equal pe
variable KEout equal ke
variable ETOTout equal etotal
variable massDensity equal density

# global scalar properties
fix GlobalPropsTimeAvg  all ave/time $s  $p  $d  v_Pout v_Tout v_Vout  v_Hout v_PEout v_KEout v_ETOTout v_massDensity  file GlobalPropsTimeAvg.prop

# calculate diffusivity
include diffusivity_msd.in.prop

# calculate viscosity
include viscosity.in.prop

# write calculated properties to a file
fix GlobalPropCalculated  all print $d  "time:${{time}}, D[H2O]:${{D_H2O}}, viscosity:${{vis}}" file GlobalPropCalculated.prop screen no


# vector properties
compute myRDF all rdf  200 7 7 8 8 7 8
fix rdfOut  all ave/time $s $p $d  c_myRDF[*] file rdf_all.rdf mode vector


run         5000000

unfix         md_npt
""".lstrip()

            with open(os.path.join(dir_path, "run.lmp"), "w") as f:
                f.write(lammps_script_content)

            for file_name in files_to_copy:
                shutil.copy(file_name, os.path.join(dir_path, file_name))

    print(f"Directories and files created successfully under: {os.path.abspath(base_dir)}")


# Example usage
temp_range = [313, 323, 333, 343, 353, 363, 373]
pressure_range = [1, 10, 20]
create_directories_with_files(temp_range, pressure_range, base_dir="simulations")
