#!/bin/bash

# --- Configuration ---
CORES=5         # Max CPU cores to use
GSFILE=${1:-draw_water.gs}
T_START=${2:-1}   # Takes 1st argument, defaults to 1
T_END=${3:-961}    # Takes 2nd argument, defaults to 772

# Calculate the total number of steps in the requested range
TOTAL_STEPS=$(( T_END - T_START + 1 ))

# Calculate how many time steps each core handles
CHUNK_SIZE=$(( (TOTAL_STEPS + CORES - 1) / CORES ))

echo "Starting parallel plotting from t=$T_START to $T_END using $CORES cores..."

for (( i=0; i<CORES; i++ )); do
    # Calculate the range for this specific core relative to T_START
    CURRENT_START=$(( T_START + (i * CHUNK_SIZE) ))
    CURRENT_END=$(( CURRENT_START + CHUNK_SIZE - 1 ))

    # Ensure we don't exceed the user-defined T_END
    if [ $CURRENT_END -gt $T_END ]; then CURRENT_END=$T_END; fi

    # Only run if the start is within the bounds
    if [ $CURRENT_START -le $T_END ]; then
        echo "Core $((i+1)): Plotting t=$CURRENT_START to $CURRENT_END"
        
        # Launch GrADS in background
	export PERL5LIB=/pkg/compiler/intel/2024/2024.0/opt/oclfpga/host/linux64/bin/perl/lib/5.30.3:/usr/lib64/perl5
        opengrads -blcx "${GSFILE} $CURRENT_START $CURRENT_END" &
    fi
done

# Wait for all background processes to finish
wait
echo "All parallel jobs for range $T_START - $T_END completed!"
