import { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import './Modal.css';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string | ReactNode;
    children: ReactNode;
    maxWidth?: string;
    headerStyle?: React.CSSProperties;
}

export default function Modal({ isOpen, onClose, title, children, maxWidth = '450px', headerStyle }: ModalProps) {
    if (!isOpen) return null;

    return createPortal(
        <div className="admin-modal-backdrop fadeIn" onClick={onClose}>
            <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()} style={{ maxWidth }}>
                <div className="admin-modal-header" style={headerStyle}>
                    {typeof title === 'string' ? <h3>{title}</h3> : title}
                    <button className="close-btn" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>
                {children}
            </div>
        </div>,
        document.body
    );
}
