/** Recursive mind-map tree renderer (Phase 9 — no graph lib dependency). */

interface MindMapNode {
  title: string;
  kind?: string;
  summary?: string;
  children?: MindMapNode[];
}

export function MindMap({ tree }: { tree: MindMapNode | null }) {
  if (!tree) return null;
  return (
    <div className="mt-3 rounded-xl border border-ink-200 bg-[#fffef9] p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-700/50">复习思维导图</p>
      <div className="ml-2">
        <MindMapNodeView node={tree} depth={0} />
      </div>
    </div>
  );
}

function MindMapNodeView({ node, depth }: { node: MindMapNode; depth: number }) {
  const isChapter = node.kind === "chapter";
  const isRoot = node.kind === "root" || depth === 0;
  return (
    <div className={depth > 0 ? "ml-4 border-l border-ink-200 pl-3" : ""}>
      <div
        className={`mindmap-node my-1 ${isChapter ? "mindmap-chapter" : ""} ${
          isRoot ? "border-campus-400 bg-campus-100 text-campus-900" : ""
        }`}
      >
        <span>{node.title}</span>
        {node.summary && depth > 0 && (
          <span className="ml-2 text-xs text-ink-700/60">— {node.summary.slice(0, 80)}</span>
        )}
      </div>
      {node.children && node.children.length > 0 && (
        <div>
          {node.children.map((child, i) => (
            <MindMapNodeView key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
