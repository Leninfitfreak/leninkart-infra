import React from 'react';

export function ClusterFilter({
  clusters,
  value,
  onChange,
}: {
  clusters: string[];
  value?: string;
  onChange: (cluster?: string) => void;
}) {
  return (
    <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
      <span>Cluster</span>
      <select value={value || ''} onChange={(e) => onChange(e.target.value || undefined)}>
        <option value="">Current Cluster (Default)</option>
        {clusters.map((cluster) => (
          <option key={cluster} value={cluster}>
            {cluster}
          </option>
        ))}
      </select>
    </label>
  );
}