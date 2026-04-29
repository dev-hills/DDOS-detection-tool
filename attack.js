import http from "k6/http";
import { sleep } from "k6";

export const options = {
  vus: 100,
  duration: "60s",
};

export default function () {
  http.get("http://34.228.247.241/");
  sleep(0.1);
}

// import http from "k6/http";

// export const options = {
//   stages: [
//     { duration: "10s", target: 20 }, // warm-up
//     { duration: "15s", target: 150 }, // large spike
//     { duration: "20s", target: 300 }, // heavy sustained
//     { duration: "10s", target: 0 }, // stop
//   ],
// };

// export default function () {
//   http.get("http://34.228.247.241/");
// }
