#version 130

in vec4 vertexColour;

uniform vec4 p3d_ColorScale;

out vec4 color;

void main()
{
    color = vertexColour*p3d_ColorScale;
}