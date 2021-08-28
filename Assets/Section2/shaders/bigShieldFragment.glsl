#version 130

in vec2 texCoord;

in vec4 vertexColour;
in vec3 vertexPos;

uniform float osg_FrameTime;
uniform vec3 mspos_player;

out vec4 color;

void main()
{
    float shieldVal = vertexColour.x;
    shieldVal = mod((shieldVal + osg_FrameTime*(0.4 + step(0.01, vertexColour.y)*0.5)), 1.0);
    shieldVal = sin(shieldVal * 3.142 );

    float alpha = min(1, vertexColour.y + 1 - clamp(length(mspos_player - vertexPos) / 25, 0, 1)) * vertexColour.z;

    color.xyz = vec3(0.2, 0.3, 1) * shieldVal;
    color.w = alpha;
}