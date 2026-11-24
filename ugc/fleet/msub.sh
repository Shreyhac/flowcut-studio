#!/bin/bash
# 23 Nov 2026: masonry submit + wait with retry on CONCURRENCY_LIMIT_REACHED (free plan = 1 generation at a time).
# usage: msub.sh <out_file> <masonry args...>   (run from the work dir) -> downloads <out_file>, prints credits
out=$1; shift; tag=$(basename ${out%.*}); for try in $(seq 1 90); do
  HOME=${MHOME:-$HOME} masonry "$@" -o $out > sub_$tag.log 2>&1; j=$(grep -oE '"job_id": "[0-9a-f-]+"' sub_$tag.log | cut -d'"' -f4)
  [ -n "$j" ] && break; grep -q CONCURRENCY_LIMIT sub_$tag.log || { echo "SUBMIT FAIL $tag"; tail -5 sub_$tag.log; exit 1; }; sleep 20; done
echo $j > job_$tag.txt; HOME=${MHOME:-$HOME} masonry job wait $j --timeout 40m --download -o $out --overwrite > wait_$tag.log 2>&1
echo "$(pwd | xargs basename) $tag $(grep -m1 -oE '"status": "[a-z]+"' wait_$tag.log) $(grep -m1 -oE '"credits_used": [0-9.]+' wait_$tag.log)"
