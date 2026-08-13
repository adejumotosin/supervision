export type Domain = {
  name: string;
  score: number;
  change: number;
  spark: number[];
};

export const history = [56, 58, 57, 61, 63, 62, 67, 66, 70, 72, 69, 74, 76, 78, 77, 79, 81, 82.4];

export const domains: Domain[] = [
  { name: "Transport", score: 78.2, change: 7.1, spark: [8, 12, 10, 15, 18, 16, 22, 19, 25, 27, 31, 34] },
  { name: "Ports", score: 91.4, change: 12.8, spark: [7, 9, 12, 11, 16, 18, 17, 24, 26, 29, 35, 39] },
  { name: "Retail", score: 69.8, change: -1.4, spark: [17, 19, 21, 22, 20, 18, 17, 16, 18, 17, 16, 15] },
  { name: "Construction", score: 86.1, change: 8.9, spark: [5, 8, 9, 12, 15, 14, 19, 18, 23, 25, 29, 32] },
  { name: "Industrial", score: 76.4, change: 3.2, spark: [9, 12, 13, 11, 16, 19, 21, 20, 22, 24, 25, 28] },
];

export const factors = [
  ["Road freight activity", "+14.2%", "Positive", "0.82"],
  ["Port throughput proxy", "+18.7%", "Positive", "0.91"],
  ["Retail footfall proxy", "-2.1%", "Negative", "0.63"],
  ["Heavy equipment activity", "+10.5%", "Positive", "0.79"],
];
