#version 330

uniform sampler2D p3d_Texture0;

in vec4 texcoord;
in vec3 origin_vec;
in vec3 eye_vec;
in vec3 eye_normal;

out vec4 f_color;

void main() {

    float f, alpha;
    vec3 uv3;
    vec2 uv;

    uv3 = texcoord.xyz / texcoord.w;
    uv = uv3.xy * .5 + .5;
    f = 10. / max(.001, pow(abs(dot(eye_vec, origin_vec)), 5.));
    alpha = min(pow(abs(dot(eye_vec, eye_normal)), 5.) * f, 1.);
    f_color = vec4(1., 1., 1., alpha) * texture(p3d_Texture0, uv);

}
