#version 330

in vec4 p3d_Vertex;
in vec4 p3d_MultiTexCoord0;
in vec4 p3d_Color;

uniform mat4 p3d_ModelViewProjectionMatrix;

out vec2 texCoord;
out vec4 vertexColour;

void main()
{
    gl_Position = p3d_ModelViewProjectionMatrix*p3d_Vertex;
    texCoord = p3d_MultiTexCoord0.st;
    vertexColour = p3d_Color;
}
