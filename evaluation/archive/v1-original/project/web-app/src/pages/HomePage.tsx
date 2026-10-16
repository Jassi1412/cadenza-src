import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import './HomePage.css';

const HomePage: React.FC = () => {
  return (
    <div className="home-page centered-home-page">
      <section className="hero-section centered-hero container">
        <div className="hero-content centered-content">
          <h1 className="hero-title logo-text floating-title">
            Cadenza
          </h1>
          <div className="hero-actions centered-actions">
            <Link to="/upload" className="btn btn-primary">
              Upload Score <ArrowRight className="btn-icon" size={18} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
