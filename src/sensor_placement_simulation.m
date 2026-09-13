%% creating dummy routes

clear;
clc;
close all;

rng(1);

numberOfRoutes = 250;

averageSlope = 0.2;
slopeVariation = 0.1;

averageIntercept = 0;
interceptVariation = 0.5;

slope = averageSlope + slopeVariation * randn(numberOfRoutes,1);

intercept = averageIntercept + interceptVariation * randn(numberOfRoutes,1);

x = linspace(-10,10,200);

figure;
hold on;
grid on;

for i = 1:numberOfRoutes

    y = slope(i)*x + intercept(i);

    plot(x,y);

end

title('historical toy routes');
xlabel('x');
ylabel('y');

%% bijective transformation to representation space

alpha = pi/2 + atan(slope);

p = intercept ./ sqrt(1 + slope.^2);

figure;

scatter(alpha,p,'filled');

grid on;

title('dummy routes in representation space');

xlabel('\alpha');
ylabel('p');

%% estimate historical map

alphaGrid = linspace(min(alpha),max(alpha),80);

pGrid = linspace(min(p),max(p),80);

[AlphaMesh,PMesh] = meshgrid(alphaGrid,pGrid);

bandwidth = 0.15;

historicalIntensity = zeros(size(AlphaMesh));

for i = 1:numberOfRoutes

    distanceSquared = ...
        (AlphaMesh - alpha(i)).^2 + ...
        (PMesh - p(i)).^2;

    historicalIntensity = ...
        historicalIntensity + ...
        exp(-distanceSquared/(2*bandwidth^2));

end

historicalIntensity = historicalIntensity / max(historicalIntensity(:));

figure;

imagesc(alphaGrid,pGrid,historicalIntensity);

set(gca,'YDir','normal');

colorbar;

title('historical intensity map');

xlabel('\alpha');
ylabel('p');

%% sensor model for one test sensor

sensorX = 0;
sensorY = 0;

sensorStrength = 0.95;
sensorRange = 1.5;

distanceToRoutes = abs(slope*sensorX - sensorY + intercept) ./ ...
    sqrt(slope.^2 + 1);

detectionProb = sensorStrength * ...
    exp(-(distanceToRoutes.^2)/(2*sensorRange^2));

missProb = 1 - detectionProb;

figure;

scatter(1:numberOfRoutes,detectionProb,'filled');

grid on;

title('detection probability for one test sensor');

xlabel('route index');
ylabel('detection probability');

%% create candidate sensor locations

sensorXValues = -10:1:10;

sensorYValues = -5:1:5;

[SensorXMesh, SensorYMesh] = meshgrid(sensorXValues, sensorYValues);

candidateSensors = [SensorXMesh(:), SensorYMesh(:)];

candidateSensorsAll = candidateSensors;

%% greedy sensor placement

numberOfSensors = 5;

candidateSensors = candidateSensorsAll;

chosenSensors = [];

currentMissProb = ones(numberOfRoutes,1);

for s = 1:numberOfSensors

    bestScore = inf;
    bestCandidate = [];

    for j = 1:size(candidateSensors,1)

        sensorX = candidateSensors(j,1);
        sensorY = candidateSensors(j,2);

        distanceToRoutes = abs(slope*sensorX - sensorY + intercept) ./ ...
            sqrt(slope.^2 + 1);

        detectionProb = sensorStrength * ...
            exp(-(distanceToRoutes.^2)/(2*sensorRange^2));

        newMissProb = currentMissProb .* (1 - detectionProb);

        score = sum(newMissProb);

        if score < bestScore
            bestScore = score;
            bestCandidate = [sensorX sensorY];
            bestNewMissProb = newMissProb;
        end

    end

    chosenSensors = [chosenSensors; bestCandidate];

    currentMissProb = bestNewMissProb;

    candidateSensors( ...
        candidateSensors(:,1) == bestCandidate(1) & ...
        candidateSensors(:,2) == bestCandidate(2), :) = [];

end

chosenSensors

historicalMissScore = sum(currentMissProb)

%% plot chosen sensors on historical routes

figure;
hold on;
grid on;

for i = 1:numberOfRoutes

    y = slope(i)*x + intercept(i);

    plot(x,y);

end

scatter(chosenSensors(:,1),chosenSensors(:,2),100,'filled','k');

title('greedy sensor placement on historical routes');

xlabel('x');
ylabel('y');

historicalSensors = chosenSensors;

%% prediction with controlled future shift

slopeChange = 0.05;

interceptChange = 0.5;

futureSlope = slope + slopeChange;

futureIntercept = intercept + interceptChange;


%% transform predicted routes

futureAlpha = pi/2 + atan(futureSlope);

futureP = futureIntercept ./ sqrt(1 + futureSlope.^2);


%% plot predicted future routes

figure;
hold on;
grid on;

for i = 1:numberOfRoutes

    futureY = futureSlope(i)*x + futureIntercept(i);

    plot(x,futureY);

end

title('predicted future routes');

xlabel('x');
ylabel('y');

%% plot predicted routes in representation space

figure;

scatter(futureAlpha,futureP,'filled');

grid on;

title('predicted routes in representation space');

xlabel('\alpha');
ylabel('p');


%% estimate predicted future intensity

futureAlphaGrid = linspace(min(futureAlpha),max(futureAlpha),80);

futurePGrid = linspace(min(futureP),max(futureP),80);

[FutureAlphaMesh,FuturePMesh] = meshgrid(futureAlphaGrid,futurePGrid);

futureIntensity = zeros(size(FutureAlphaMesh));

for i = 1:numberOfRoutes

    distanceSquared = ...
        (FutureAlphaMesh - futureAlpha(i)).^2 + ...
        (FuturePMesh - futureP(i)).^2;

    futureIntensity = ...
        futureIntensity + ...
        exp(-distanceSquared/(2*bandwidth^2));

end

futureIntensity = futureIntensity / max(futureIntensity(:));

figure;

imagesc(futureAlphaGrid,futurePGrid,futureIntensity);

set(gca,'YDir','normal');

colorbar;

title('predicted future intensity');

xlabel('\alpha');
ylabel('p');

%% greedy sensor placement for predicted future routes

candidateSensorsFuture = candidateSensorsAll;

futureChosenSensors = [];

futureCurrentMissProb = ones(numberOfRoutes,1);

for s = 1:numberOfSensors

    bestScore = inf;
    bestCandidate = [];

    for j = 1:size(candidateSensorsFuture,1)

        sensorX = candidateSensorsFuture(j,1);
        sensorY = candidateSensorsFuture(j,2);

        distanceToRoutes = abs(futureSlope*sensorX - sensorY + futureIntercept) ./ ...
            sqrt(futureSlope.^2 + 1);

        detectionProb = sensorStrength * ...
            exp(-(distanceToRoutes.^2)/(2*sensorRange^2));

        newMissProb = futureCurrentMissProb .* (1 - detectionProb);

        score = sum(newMissProb);

        if score < bestScore
            bestScore = score;
            bestCandidate = [sensorX sensorY];
            bestNewMissProb = newMissProb;
        end

    end

    futureChosenSensors = [futureChosenSensors; bestCandidate];

    futureCurrentMissProb = bestNewMissProb;

    candidateSensorsFuture( ...
        candidateSensorsFuture(:,1) == bestCandidate(1) & ...
        candidateSensorsFuture(:,2) == bestCandidate(2), :) = [];

end

futureChosenSensors

futureMissScore = sum(futureCurrentMissProb)

%% plot future sensors on predicted routes

figure;
hold on;
grid on;

for i = 1:numberOfRoutes

    futureY = futureSlope(i)*x + futureIntercept(i);

    plot(x,futureY);

end

scatter(futureChosenSensors(:,1),futureChosenSensors(:,2),100,'filled','k');

title('greedy sensor placement on predicted future routes');

xlabel('x');
ylabel('y');

%% combine historical and predicted routes

baseSlope = [slope; futureSlope];

baseIntercept = [intercept; futureIntercept];


%% create uncertainty routes around history and prediction

uncertaintySlopeShift = [-0.03 0 0.03];

uncertaintyInterceptShift = [-0.4 0 0.4];

uncertainSlope = [];

uncertainIntercept = [];

for a = 1:length(uncertaintySlopeShift)

    for b = 1:length(uncertaintyInterceptShift)

        uncertainSlope = [uncertainSlope; ...
            baseSlope + uncertaintySlopeShift(a)];

        uncertainIntercept = [uncertainIntercept; ...
            baseIntercept + uncertaintyInterceptShift(b)];

    end

end
%% transform uncertainty routes

uncertainAlpha = pi/2 + atan(uncertainSlope);

uncertainP = uncertainIntercept ./ sqrt(1 + uncertainSlope.^2);


%% plot uncertainty routes

figure;
hold on;
grid on;

for i = 1:length(uncertainSlope)

    uncertainY = uncertainSlope(i)*x + uncertainIntercept(i);

    plot(x,uncertainY);

end

title('uncertainty routes around historical and predicted routes');

xlabel('x');
ylabel('y');


%% plot uncertainty routes in representation space

figure;

scatter(uncertainAlpha,uncertainP,'filled');

grid on;

title('uncertainty routes in representation space');

xlabel('\alpha');
ylabel('p');

%% estimate uncertainty intensity

uncertainAlphaGrid = linspace(min(uncertainAlpha),max(uncertainAlpha),80);

uncertainPGrid = linspace(min(uncertainP),max(uncertainP),80);

[UncertainAlphaMesh,UncertainPMesh] = meshgrid(uncertainAlphaGrid,uncertainPGrid);

uncertaintyIntensity = zeros(size(UncertainAlphaMesh));

for i = 1:length(uncertainAlpha)

    distanceSquared = ...
        (UncertainAlphaMesh - uncertainAlpha(i)).^2 + ...
        (UncertainPMesh - uncertainP(i)).^2;

    uncertaintyIntensity = ...
        uncertaintyIntensity + ...
        exp(-distanceSquared/(2*bandwidth^2));

end

uncertaintyIntensity = uncertaintyIntensity / max(uncertaintyIntensity(:));


%% plot uncertainty intensity

figure;

imagesc(uncertainAlphaGrid,uncertainPGrid,uncertaintyIntensity);

set(gca,'YDir','normal');

colorbar;

title('uncertainty intensity map');

xlabel('\alpha');
ylabel('p');

%% greedy sensor placement for uncertainty routes

candidateSensorsUncertainty = candidateSensorsAll;

uncertaintyChosenSensors = [];

uncertaintyCurrentMissProb = ones(length(uncertainSlope),1);

for s = 1:numberOfSensors

    bestScore = inf;
    bestCandidate = [];

    for j = 1:size(candidateSensorsUncertainty,1)

        sensorX = candidateSensorsUncertainty(j,1);
        sensorY = candidateSensorsUncertainty(j,2);

        distanceToRoutes = ...
            abs(uncertainSlope*sensorX - sensorY + uncertainIntercept) ./ ...
            sqrt(uncertainSlope.^2 + 1);

        detectionProb = sensorStrength * ...
            exp(-(distanceToRoutes.^2)/(2*sensorRange^2));

        newMissProb = uncertaintyCurrentMissProb .* (1 - detectionProb);

        score = sum(newMissProb);

        if score < bestScore
            bestScore = score;
            bestCandidate = [sensorX sensorY];
            bestNewMissProb = newMissProb;
        end

    end

    uncertaintyChosenSensors = [uncertaintyChosenSensors; bestCandidate];

    uncertaintyCurrentMissProb = bestNewMissProb;

    candidateSensorsUncertainty( ...
        candidateSensorsUncertainty(:,1)==bestCandidate(1) & ...
        candidateSensorsUncertainty(:,2)==bestCandidate(2), :) = [];

end

uncertaintyChosenSensors

uncertaintyMissScore = sum(uncertaintyCurrentMissProb)

%% plot uncertainty sensor placement

figure;
hold on;
grid on;

for i = 1:length(uncertainSlope)

    uncertainY = uncertainSlope(i)*x + uncertainIntercept(i);

    plot(x,uncertainY);

end

scatter(uncertaintyChosenSensors(:,1), ...
    uncertaintyChosenSensors(:,2), ...
    250, ...
    [1 0.2 0.8], ...
    'filled', ...
    'MarkerEdgeColor','k', ...
    'LineWidth',1.5);

title('uncertainty sensor placement');

xlabel('x');
ylabel('y');

%% normalized miss scores

historicalNormalizedMiss = historicalMissScore / numberOfRoutes;

futureNormalizedMiss = futureMissScore / numberOfRoutes;

uncertaintyNormalizedMiss = uncertaintyMissScore / length(uncertainSlope);

historicalNormalizedMiss

futureNormalizedMiss

uncertaintyNormalizedMiss


%% compare normalized miss scores

scores = [historicalNormalizedMiss ...
    futureNormalizedMiss ...
    uncertaintyNormalizedMiss];

figure;

bar(scores);

xticklabels({'historical','prediction','uncertainty'});

ylabel('normalized miss score');

title('normalized miss score comparison');

grid on;