#version 130

in vec4 vertexColour;

uniform vec4 p3d_ColorScale;
uniform float power;
//in float mew;

out vec4 color;

void main()
{
    //color = vertexColour*p3d_ColorScale;
    //color = vec4(0, mew*200, 0, 1);
    float value = vertexColour.w*power;
    vec3 colour = vec3(1, 1, 1);
    colour.x = (value - 1 + vertexColour.x)/max(0.001, 1 - value);
    colour.y = (value - 1 + vertexColour.y)/max(0.001, 1 - value);
    colour.z = (value - 1 + vertexColour.z)/max(0.001, 1 - value);
    color.xyz = colour*p3d_ColorScale.xyz;
    color.w = p3d_ColorScale.w;
}
