#version 130

in vec4 p3d_Vertex;
in vec4 p3d_MultiTexCoord0;

uniform mat4 p3d_ModelViewProjectionMatrix;

out vec2 texCoord;

void main()
{
    gl_Position = p3d_ModelViewProjectionMatrix*p3d_Vertex;
    texCoord = p3d_MultiTexCoord0.st;
}