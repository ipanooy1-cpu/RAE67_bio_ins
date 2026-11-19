/** Joint axes are local to the parent link, not world coordinates. */
export type RotationAxis = 'x' | 'y' | 'z';
export function jointRotation(degrees: number, axis: RotationAxis): [number, number, number] {
  const radians = degrees * Math.PI / 180;
  return [axis === 'x' ? radians : 0, axis === 'y' ? radians : 0, axis === 'z' ? radians : 0];
}
