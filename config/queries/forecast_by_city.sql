SELECT city, CAST(SUM(trips_forecast) AS BIGINT) AS forecast_trips
FROM demo_catalog.apex_ride_hailing.gold_demand_forecast
GROUP BY 1 ORDER BY 2 DESC;
