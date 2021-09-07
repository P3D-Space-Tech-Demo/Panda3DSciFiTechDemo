#version 330

// Uniform inputs
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;

// Vertex inputs
in vec4 p3d_Vertex;

// Output to fragment shader
out vec4 texcoord;
out vec3 origin_vec;
out vec3 eye_vec;
out vec3 eye_normal;

void main(void)
{
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord.xyw = gl_Position.xyw;
    texcoord.z = gl_Position.w;
    origin_vec = normalize(p3d_ModelViewMatrix * vec4(0., 0., 0., 1.)).xyz;
    eye_vec = normalize(p3d_ModelViewMatrix * p3d_Vertex).xyz;
    eye_normal = normalize(p3d_NormalMatrix * p3d_Vertex.xyz);
}
