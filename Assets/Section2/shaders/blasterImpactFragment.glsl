#version 130

in vec2 texCoord;

uniform sampler2D sourceTex1;
uniform sampler2D sourceTex2;
uniform float startTime;
uniform float duration;
uniform float expansionFactor;
uniform float randomisation1;
uniform float randomisation2;

uniform float osg_FrameTime;

out vec4 color;

void main()
{
    float blastPerc = clamp(max(0, osg_FrameTime - startTime) / duration, 0, 1);

    float scalar = ((1 - blastPerc) * expansionFactor) + 1;

    float angle1 = randomisation1;
    float angle2 = randomisation2;

    mat2 rotation1 = mat2(cos(angle1), -sin(angle1),
                          sin(angle1), cos(angle1));
    mat2 rotation2 = mat2(cos(angle2), -sin(angle2),
                          sin(angle2), cos(angle2));

    vec4 noisePix1 = texture(sourceTex1, rotation1*(texCoord - vec2(0.5, 0.5))*scalar + vec2(0.5, 0.5));
    vec4 noisePix2 = texture(sourceTex2, rotation2*(texCoord - vec2(0.5, 0.5))*scalar + vec2(0.5, 0.5));

    float noisePixCombined = max(noisePix1.x, noisePix2.x);

    float dist = ((texCoord.s - 0.5)*(texCoord.s - 0.5) + (texCoord.t - 0.5)*(texCoord.t - 0.5))*5 + 1 - blastPerc;

    float val = min(1.0 - smoothstep(0, 0.1, dist - 1), smoothstep(blastPerc*0.99, 1, dist + 1 - pow(blastPerc, 0.1)));

    val *= 1.0 - max(0, blastPerc - 0.1)/0.9;//cos(blastPerc*1.571);

    val *= smoothstep(-0.1, 0, noisePixCombined - blastPerc*blastPerc);

    vec3 colour = vec3(cos(val*1.571 + 3.142)*0.7 + 0.7, cos(val*1.571 + 3.142) + 1, sin(val*1.571));

    color.xyz = colour;
    color.w = 1;
}