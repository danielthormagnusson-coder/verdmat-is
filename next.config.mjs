/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "d1u57vh96em4i1.cloudfront.net" },
    ],
  },
};

export default nextConfig;
