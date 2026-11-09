import Link from "next/link";

export default function NotFound() {
  return (
    <section className="card stack" aria-labelledby="niet-gevonden">
      <h1 id="niet-gevonden">Pagina niet gevonden</h1>
      <p>Deze pagina bestaat niet (meer).</p>
      <p>
        <Link href="/" className="losse-link">
          Naar Home
        </Link>
      </p>
    </section>
  );
}
