#version 130

in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 p3d_Color;

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 p3d_ModelMatrixInverseTranspose;

uniform float flameScalar;

out vec4 vertexColour;
out vec3 normal;

void main()
{
    vec4 adjustedVertex = vec4(p3d_Vertex);
    adjustedVertex.y -= (1.0 - pow(p3d_Color.w, 0.8))*2;
    adjustedVertex.y *= flameScalar;
    adjustedVertex.xz *= flameScalar*0.5 + 0.5;
    gl_Position = p3d_ModelViewProjectionMatrix*adjustedVertex;
    normal = normalize(p3d_NormalMatrix*p3d_Normal);
    vertexColour = p3d_Color;
}