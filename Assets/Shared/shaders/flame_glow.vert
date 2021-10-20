#version 130

in vec4 p3d_Vertex;
in vec4 p3d_Color;

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat4 trans_world_to_model;
uniform mat4 trans_world_to_clip;

uniform float power;
uniform vec3 direction;
uniform float flameScalar;

//out float mew;

out float intensity;

void main()
{
    vec4 zeroPt = p3d_ModelMatrix*vec4(0, 0, 0, 1);
    vec4 basePt = p3d_ModelMatrix*p3d_Vertex;

    float dotProd = dot((basePt - zeroPt).xyz*flameScalar, direction);
    float lengthScalar = length(p3d_Vertex.xyz)*flameScalar;
    dotProd *= dotProd*dotProd;

    vec4 vert = vec4(p3d_Vertex);
    vert.xy *= 1 + (power*0.5 + 0.5)*0.25;
    vert = p3d_ModelMatrix*vert;
    vert += vec4(direction*max(0, dotProd)*40, 0)*power;

    gl_Position = trans_world_to_clip*vert;

    intensity = p3d_Color.x;
}
