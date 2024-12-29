mkdir -p summaries
for i in {1..12}
do
    python3 present.py -i commits-issues-prs/bounswe-bounswe2024group$i.json -u people.json > summaries/group$i.md
done
