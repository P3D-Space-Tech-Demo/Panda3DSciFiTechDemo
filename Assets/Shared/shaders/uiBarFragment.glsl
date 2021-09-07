#version 330

in vec2 texCoord;
in vec4 vertexColour;

uniform vec4 p3d_ColorScale;

uniform vec3 colourTop;
uniform vec3 colourBottom;
uniform float cornerSize;
uniform float edgeSoftness;
uniform float aspectRatio;

out vec4 color;

void main()
{
    float colourPerc = texCoord.t;

    float widthAdjustment = 1.0 / max(1, abs(aspectRatio));
    float heightAdjustment = min(1, abs(aspectRatio));

    float cornerValueL = smoothstep(0, cornerSize*widthAdjustment, texCoord.s);
    float cornerValueR = 1.0 - smoothstep(1 - cornerSize*widthAdjustment, 1, texCoord.s);
    float cornerValueT = smoothstep(0, cornerSize*heightAdjustment, texCoord.t);
    float cornerValueB = 1.0 - smoothstep(1 - cornerSize*heightAdjustment, 1, texCoord.t);

    float cornerValue = cornerValueB * cornerValueB * cornerValueL * cornerValueL * cornerValueT * cornerValueT * cornerValueR * cornerValueR;
    cornerValue = smoothstep(0, edgeSoftness, cornerValue);

    color.xyz = colourTop * colourPerc + (1.0 - colourPerc) * colourBottom;
    color.xyz *= p3d_ColorScale.xyz * vertexColour.xyz;
    //color.xyz = vec3(0, cornerValue, 0);
    color.w = cornerValue*p3d_ColorScale.w;
}
