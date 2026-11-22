type Props = {
  title: string;
  url: string | null;
  fileUrl: string | null;
  archived: boolean;
};

/**
 * NLINK-04, NBASE-08: the norm a rule cites. "Ver norma" opens the attached file, else the source
 * URL; a norm with neither shows only its title. An archived norm keeps showing, marked "(arquivada)".
 */
export function NormLink({ title, url, fileUrl, archived }: Props) {
  const href = fileUrl ?? url;
  return (
    <span className="norm-link">
      <span className="norm-title">{title}</span>
      {href && (
        <>
          {" "}
          <a href={href} target="_blank" rel="noopener noreferrer">
            Ver norma
          </a>
        </>
      )}
      {archived && (
        <>
          {" "}
          <span className="norm-archived">(arquivada)</span>
        </>
      )}
    </span>
  );
}
