#!/usr/bin/env bash

export PGDATABASE=panorama
export PGUSER=panorama
export PGPORT="${PGPORT:-5454}"
export PGPASSWORD="${PGPASSWORD:-insecure}"
# export PGHOST="${PGHOST:-localhost}"
export PGHOSTADDR=${PGHOSTADDR:-127.0.0.1}

psql -c "CREATE TABLE IF NOT EXISTS panoramas_region_external (LIKE panoramas_region)"
COLS=region_type,left_top_x,left_top_y,right_top_x,right_top_y,left_bottom_x,left_bottom_y,right_bottom_x,right_bottom_y,detected_by,pano_id

TEST_ONLY=true

if [ "$TEST_ONLY" = true ]
then
    FILE=test_pano.txt
    egrep 'pano_id|TMX7316010203-001900_pano_0005_000806|TMX7316010203-001899_pano_0000_000088|TMX7316010203-001900_pano_0006_000313' pano_meta_08.txt > $FILE
    echo "Processing $FILE file..."
    psql -c "TRUNCATE panoramas_region_external"
    psql -c "\COPY panoramas_region_external FROM '$FILE' WITH DELIMITER ','  CSV HEADER"
    psql -c "INSERT INTO panoramas_region($COLS) SELECT $COLS FROM panoramas_region_external"
else
    FILES=pano_meta_*.txt
    for f in $FILES
    do
      echo "Processing $f file..."
      psql -c "TRUNCATE panoramas_region_external"
      psql -c "\COPY panoramas_region_external FROM '$f' WITH DELIMITER ','  CSV HEADER"
      psql -c "INSERT INTO panoramas_region($COLS) SELECT $COLS FROM panoramas_region_external"
    done
fi

psql -c "DROP TABLE panoramas_region_external"

echo "Remove duplicates from panoramas_region"
psql -c "DELETE FROM panoramas_region
        WHERE id IN (
          SELECT id
          FROM (
            SELECT id, ROW_NUMBER() OVER(
              PARTITION BY region_type
                         , left_top_x
                         , left_top_y
                         , right_top_x
                         , right_top_y
                         , left_bottom_x
                         , left_bottom_y
                         , right_bottom_x
                         , right_bottom_y
                         , detected_by
                         , pano_id
              ORDER BY  id ) AS row_num
            FROM panoramas_region ) t
            WHERE t.row_num > 1 )
"

echo "Set status to detected for panoramas with upodated regions"
psql -c "UPDATE panoramas_panorama
SET status = 'detected', status_changed = NOW()
WHERE pano_id IN (SELECT DISTINCT(pano_id) as pano_id FROM panoramas_region WHERE detected_by = 'CTO AI Team')
"
