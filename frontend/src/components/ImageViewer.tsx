import React, { useRef, useEffect } from 'react';
import { ProcessResult } from '../types';

interface ImageViewerProps {
  result: ProcessResult | null;
  originalImage: string | null;
}

const ImageViewer: React.FC<ImageViewerProps> = ({ result, originalImage }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !result) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw original image if available
    if (originalImage) {
      const img = new Image();
      img.onload = () => {
        ctx.globalAlpha = 0.3;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        ctx.globalAlpha = 1.0;
        drawDetectionResults(ctx, result);
      };
      img.src = originalImage;
    } else {
      drawDetectionResults(ctx, result);
    }
  }, [result, originalImage]);

  const drawDetectionResults = (ctx: CanvasRenderingContext2D, result: ProcessResult) => {
    // Draw snapped segments
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    
    result.snapped_segments.forEach(([x1, y1, x2, y2]) => {
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    });

    // Draw raw lines (faint)
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.3;
    
    result.raw_lines.forEach(([x1, y1, x2, y2]) => {
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    });
    
    ctx.globalAlpha = 1.0;

    // Draw nodes if graph exists
    if (result.graph) {
      ctx.fillStyle = '#10b981';
      result.graph.nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 3, 0, 2 * Math.PI);
        ctx.fill();
      });
    }

    // Draw rooms if available
    if (result.graph && result.graph.rooms.length > 0) {
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 1;
      ctx.fillStyle = '#fef3c7';
      ctx.globalAlpha = 0.2;
      
      result.graph.rooms.forEach(room => {
        ctx.beginPath();
        room.polygon.forEach((point, index) => {
          if (index === 0) {
            ctx.moveTo(point.x, point.y);
          } else {
            ctx.lineTo(point.x, point.y);
          }
        });
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      });
      
      ctx.globalAlpha = 1.0;
    }

    // Draw gaps if available (Unclosed loops)
    if (result.graph && result.graph.gaps && result.graph.gaps.length > 0) {
      ctx.strokeStyle = '#ef4444'; // Red
      ctx.lineWidth = 2;
      ctx.fillStyle = 'rgba(239, 68, 68, 0.4)';
      
      result.graph.gaps.forEach((gap) => {
        ctx.beginPath();
        ctx.arc(gap.x, gap.y, 8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      });
    }
  };

  if (!result) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100 rounded-lg">
        <p className="text-gray-500">Upload a floor plan to see detection results</p>
      </div>
    );
  }

  return (
    <div className="relative bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="absolute top-2 left-2 bg-white px-2 py-1 rounded shadow-sm z-10">
        <span className="text-xs font-medium text-gray-600">
          {result.detection_mode === 'opencv' ? 'OpenCV Detection' : 'Fallback Mode'}
        </span>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="w-full h-full rounded-lg"
      />
    </div>
  );
};

export default ImageViewer;
