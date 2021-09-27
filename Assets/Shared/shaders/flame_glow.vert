#version 130

in vec4 p3d_Vertex;
in vec4 p3d_Color;

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;

uniform float power;
uniform vec3 direction;

//out float mew;

out vec4 vertexColour;

void main()
{
    vec4 zeroPt = p3d_ModelViewMatrix*vec4(0, 0, 0, 1);
    vec4 basePt = p3d_ModelViewMatrix*p3d_Vertex;

    vec4 projectedDirection = p3d_ModelViewMatrix*vec4(direction, 1);

    float dotProd = dot((basePt - zeroPt).xy, projectedDirection.xy);
    float scalar = cos(dotProd*1.571 + 3.142) + 1;//pow(dotProd, 2);
    scalar *= scalar;
    //scalar *= 10;
    //scalar = pow(scalar, 5);
    scalar *= step(0, dotProd);
    //mew = scalar;
    vec4 adjustedVertex = vec4(p3d_Vertex);
    adjustedVertex.xy += projectedDirection.xy*(scalar*10*(1.0 - max(0, projectedDirection.z)))*power;
    adjustedVertex.xy *= (power*0.5 + 0.5)*0.5*abs(projectedDirection.z);
    //adjustedVertex.y *= 1 + abs(adjustedVertex.x);

    gl_Position = p3d_ModelViewProjectionMatrix*adjustedVertex;

    vertexColour = p3d_Color;
}
