#version 130

in vec2 texCoord;

uniform sampler2D p3d_Texture0;
in float speed;

uniform float maxSpeed;

uniform float movementOffset;

out vec4 color;

void main()
{
    float speedPerc = speed / maxSpeed;
    vec2 uvs = vec2(texCoord);
    //float speedScalar = 1.0 - speedPerc*0.5;
    //uvs.t *= speedScalar;
    uvs.t += movementOffset;
    uvs.s *= 3;
    vec4 dustPix = texture2D(p3d_Texture0, uvs);

    float threshold = 1.0 - speedPerc;
    float fade = (step(threshold, dustPix.z))*(dustPix.z - threshold)*dustPix.y;

    color.xyz = vec3(1, 1, 1);
    //color.xyz = vec3(0, dustPix.y, 0);
    color.w = fade;
}