SELECT city, COUNT(*) AS trips
FROM demo_catalog.apex_ride_hailing.trips_curated_gold
GROUP BY 1 ORDER BY 2 DESC;
