#version 130

in vec2 texCoord;

uniform sampler2D sourceTex1;
uniform sampler2D sourceTex2;
uniform float startTime;
uniform float duration;
uniform float starDuration;
uniform float expansionFactor;
uniform float rotationRate;
uniform float fireballBittiness;
uniform vec2 randomisation1;
uniform vec2 randomisation2;

uniform float osg_FrameTime;

out vec4 color;

void main()
{
    float starPerc = min(starDuration, osg_FrameTime - startTime) / starDuration;
    starPerc = cos(starPerc*1.571 + 3.142) + 1;

    float fireballPerc = clamp(max(0, (osg_FrameTime - startTime) - starDuration) / duration, 0, 1);

    float angle1 = fireballPerc * rotationRate;
    float angle2 = -fireballPerc * rotationRate * 0.8;

    mat2 rotation1 = mat2(cos(angle1), -sin(angle1),
                          sin(angle1), cos(angle1));
    mat2 rotation2 = mat2(cos(angle2), -sin(angle2),
                          sin(angle2), cos(angle2));

    float scalar = (1 / (1 + fireballPerc * expansionFactor)) * fireballBittiness;

    vec4 noisePix1 = texture(sourceTex1, (rotation1*(texCoord*2 - vec2(1, 1)))*scalar + randomisation1);
    vec4 noisePix2 = texture(sourceTex2, (rotation2*(texCoord*2 - vec2(1, 1)))*(0.1 + scalar*0.9) + randomisation2);

    vec4 noisePixCombined = noisePix1 * noisePix2;

    float value = noisePixCombined.w;

    float dist = min(1, ((texCoord.s - 0.5)*(texCoord.s - 0.5) + (texCoord.t - 0.5)*(texCoord.t - 0.5)));

    float threshold = dist;

    float thresholdCosVal = cos(fireballPerc*1.571 + 3.142)*0.5 + 0.5;

    threshold = min(1.1, threshold + thresholdCosVal);

    value = smoothstep(threshold - 0.1, threshold, value);
    value = (1.0 - smoothstep(0.001*noisePixCombined.w + fireballPerc*0.5, 0.002*noisePixCombined.w + fireballPerc*0.5, dist))*value;

    vec3 colour = vec3(sin(value*1.571)*0.5 + 0.5,
                        max(0, value - 0.2)/(0.8),
                        max(0, value - 0.9)/0.1);
    colour = colour*smoothstep(0, 0.3, value);
    colour *= 1.0 - max(0, fireballPerc - 0.8)/0.2;

    colour += vec3(1, 0.7*(1.0 - fireballPerc), 0.2*(1.0 - fireballPerc))*clamp(1.0 - dist*(5 + 150*(cos(pow(fireballPerc, 0.1)*1.571 + 1.571)*0.5 + 0.5)), 0, 1)*(1.0 - pow(fireballPerc, 0.2));

    float starVal = max(0, 1.0 - abs(texCoord.s - 0.5)*abs(texCoord.t - 0.5)*(500 - 500*starPerc));
    //starVal *= starVal;
    starVal *= (1.0 - dist*(80 + cos(starPerc*3.1 + 2.9)*60));
    starVal *= (1.0 - fireballPerc);
    starVal = smoothstep(0.8, 0.9, starVal);

    colour += vec3(starVal, starVal, starVal);

    color.xyz = colour;
    color.w = 1;
}