#version 130

in vec4 p3d_Vertex;
in vec4 p3d_Color;

uniform mat4 p3d_ModelViewProjectionMatrix;

out vec4 vertexColour;

void main()
{
    gl_Position = p3d_ModelViewProjectionMatrix*p3d_Vertex;
    vertexColour = p3d_Color;
}