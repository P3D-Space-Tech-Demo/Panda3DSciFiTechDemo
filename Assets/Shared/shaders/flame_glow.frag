#version 130

in float intensity;

uniform vec4 p3d_ColorScale;
uniform vec3 flameColourGradients;
uniform float power;
//in float mew;

out vec4 color;

void main()
{
    float value = intensity*power;
    vec3 colour = vec3(1, 1, 1);
    colour.x = (value - 1 + flameColourGradients.x)/max(0.001, 1 - value);
    colour.y = (value - 1 + flameColourGradients.y)/max(0.001, 1 - value);
    colour.z = (value - 1 + flameColourGradients.z)/max(0.001, 1 - value);
    color.xyz = colour*p3d_ColorScale.xyz;
    color.w = p3d_ColorScale.w;
}
