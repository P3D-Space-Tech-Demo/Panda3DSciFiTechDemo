#version 130

in vec4 vertexColour;
in vec3 normal;

uniform vec4 p3d_ColorScale;

out vec4 color;

void main()
{
    float value = normal.z*normal.z*normal.z;
    vec3 colour = vec3(1, 1, 1);
    colour.x = (value - 1 + vertexColour.x)/max(0.001, 1 - value);
    colour.y = (value - 1 + vertexColour.y)/max(0.001, 1 - value);
    colour.z = (value - 1 + vertexColour.z)/max(0.001, 1 - value);
    color.xyz = colour*p3d_ColorScale.xyz;
    //color.xyz = vec3(0, vertexColour.w, 0);
    color.w = 1;
}