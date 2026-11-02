% Runs the unchanged v0.1 script legacy/matlab/sensor_placement_simulation.m
% in GNU Octave with plotting functions stubbed out, then writes the
% routes and selected sensors so the Python port can be compared.
% Environment: LEGACY_DIR, STUB_DIR, OUT_DIR.
addpath(getenv('STUB_DIR'));
addpath(getenv('LEGACY_DIR'));
warning('off', 'all');
sensor_placement_simulation;
o = getenv('OUT_DIR');
dlmwrite(fullfile(o, 'slope.csv'), slope, 'precision', 17);
dlmwrite(fullfile(o, 'intercept.csv'), intercept, 'precision', 17);
dlmwrite(fullfile(o, 'hist_sensors.csv'), historicalSensors, 'precision', 17);
dlmwrite(fullfile(o, 'future_sensors.csv'), futureChosenSensors, 'precision', 17);
dlmwrite(fullfile(o, 'unc_sensors.csv'), uncertaintyChosenSensors, 'precision', 17);
dlmwrite(fullfile(o, 'scores.csv'), [historicalNormalizedMiss futureNormalizedMiss uncertaintyNormalizedMiss], 'precision', 17);
