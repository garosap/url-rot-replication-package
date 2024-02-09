#!/bin/bash

# Define an array of venues
venues=("ASEJ" "ESE" "IJSEKE" "ISSE" "IST" "JSS" "REJ" "NOTES" "SMR" "SOSYM" "SPE" "SQJ" "STVR" "SW" "TOSEM" "TSE" "ASE" "ESEM" "FASE" "FSE" "GPCE" "ICPC" "ICSE" "ICSM" "ICSME" "ICST" "ISSTA" "MODELS" "MSR" "RE" "SANER" "SCAM" "SSBSE" "WCRE")

# Create logs directory if it does not exist
mkdir -p ./logs/parse_xml

# Loop through the array and start each command in the background, with logs
for venue in "${venues[@]}"; do
    nohup python3 -u 2_pdf_to_xml.py --dir ../data --Minyear 1971 --Maxyear 2023 --venue "$venue" > "./logs/parse_xml/${venue}_xml_parsing_log.txt" 2>&1 &
done

echo "All grobids started."

