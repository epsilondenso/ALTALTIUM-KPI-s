#!/usr/bin/bash
echo "Enter a short commit message"
read COMMIT
rm -r ../kpis_densel
mkdir ../kpis_densel
cp -r * ../kpis_densel
git checkout densel
cp -r ../kpis_densel ./
git add ./kpis_densel
git commit -m "$COMMIT"
git push crm densel
rm -r ./kpis_densel
git checkout main